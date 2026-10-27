import asyncio
from typing import Annotated
from litestar import get,post,Request
from litestar.datastructures import UploadFile
from litestar.params import Body
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException
from sqlalchemy import select,func
from app.models import *
from app.schemas import ApplicationInput,ReviewInput,EvidenceInput
from app.security.auth import identity
from app.services.cases import get_case,ensure_editable,serialize,upload,review
from app.workflows.engine import run,case_records,invalidate
from app.services.policy.engine import DEFAULT_POLICY

# Single analysis/upload critical section per process. Compose runs one worker.
lock=asyncio.Lock()
@get('/api/health',sync_to_thread=True)
def health()->dict:
    with Session() as s:s.execute(select(1))
    return {'status':'ok','llm_mode':settings.llm_mode,'synthetic_only':True}
@get('/api/applications',sync_to_thread=True)
def applications(request:Request,offset:int=0,limit:int=50,pan:str|None=None)->dict:
    identity(request)
    if offset<0 or not 1<=limit<=100:raise ClientException('Invalid pagination',status_code=422)
    with Session() as s:
        rows=list(s.scalars(select(Application).order_by(Application.created_at.desc())))
        if pan:rows=[a for a in rows if a.data.get('journey',{}).get('pan','').casefold()==pan.strip().casefold()]
        filtered_total=len(rows);rows=rows[offset:offset+limit]
        counts=dict(s.execute(select(Application.status,func.count()).group_by(Application.status)).all())
        return {'items':[serialize(r) for r in rows],'total':filtered_total,'counts':counts,'offset':offset,'limit':limit}
@post('/api/applications',sync_to_thread=True)
def create(request:Request,data:ApplicationInput)->dict:
    identity(request)
    with Session.begin() as s:
        a=Application(id=uid(),data=data.model_dump(mode='json'),status='draft',revision=0);s.add(a);s.flush();audit(s,a.id,'application_created',actor=identity(request));return serialize(a)
@get('/api/applications/{case_id:str}',sync_to_thread=True)
def workspace(request:Request,case_id:str)->dict:
    identity(request)
    with Session() as s:
        a=get_case(s,case_id)
        result=serialize(a)
        for key,cls in [('documents',Document),('agent_runs',AgentRun),('evidence_requests',EvidenceRequest),('cam_versions',CamVersion),('decisions',ReviewDecision)]:result[key]=[serialize(x) for x in case_records(s,cls,case_id)]
        return result
@post('/api/applications/{case_id:str}/documents')
async def documents_upload(request:Request,case_id:str,data:Annotated[UploadFile,Body(media_type=RequestEncodingType.MULTI_PART)],kind:str,replaces:str|None=None)->dict:
    identity(request)
    raw=await data.read(settings.max_upload+1)
    async with lock:return await asyncio.to_thread(upload,case_id,data.filename or 'document',kind,raw,replaces)
@get('/api/applications/{case_id:str}/documents',sync_to_thread=True)
def documents(request:Request,case_id:str)->dict:
    identity(request)
    with Session() as s:
        get_case(s,case_id);return {'items':[serialize(d) for d in case_records(s,Document,case_id)]}
@post('/api/applications/{case_id:str}/runs',status_code=200)
async def start_run(request:Request,case_id:str)->dict:
    identity(request)
    if lock.locked():raise ClientException('Analysis busy; retry shortly',status_code=409)
    async with lock:
        with Session.begin() as s:
            a=get_case(s,case_id)
            if a.status in ['approved','rejected']:raise ClientException('Finalized case',status_code=409)
            current=s.query(CamVersion).filter_by(case_id=case_id,revision=a.revision).first()
            if current and current.data['policy_version']!=DEFAULT_POLICY['version']:invalidate(s,a,'cashflow','Configured policy version changed')
            if a.analyzed_revision==a.revision:return {'status':a.status,'revision':a.revision,'reused':True}
        return await asyncio.to_thread(run,case_id)
@get('/api/applications/{case_id:str}/runs',sync_to_thread=True)
def runs(request:Request,case_id:str)->dict:
    identity(request)
    with Session() as s:
        a=get_case(s,case_id);return {'status':a.status,'revision':a.revision,'items':[serialize(r) for r in case_records(s,AgentRun,case_id)]}
@get('/api/applications/{case_id:str}/evidence',sync_to_thread=True)
def evidence(request:Request,case_id:str,offset:int=0,limit:int=100)->dict:
    identity(request)
    if offset<0 or not 1<=limit<=500:raise ClientException('Invalid pagination',status_code=422)
    with Session() as s:
        get_case(s,case_id)
        docs={d.id:d for d in case_records(s,Document,case_id)}
        items=[{**x.data,'superseded':docs[x.document_id].status=='superseded'} for cls in [ExtractedField,Transaction] for x in case_records(s,cls,case_id)]
        return {'items':items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit}
@get('/api/applications/{case_id:str}/analysis/{section:str}',sync_to_thread=True)
def analysis(request:Request,case_id:str,section:str)->dict:
    identity(request)
    mapping={'reconciliation':ReconciliationFinding,'financial':FinancialMetric,'risk':RiskFlag,'policy':PolicyEvaluation}
    if section not in mapping:raise ClientException('Unknown analysis section',status_code=404)
    with Session() as s:
        a=get_case(s,case_id);return {'revision':a.revision,'stale':a.analyzed_revision!=a.revision,'items':[serialize(r) for r in case_records(s,mapping[section],case_id,a.revision)]}
@post('/api/applications/{case_id:str}/evidence-requests')
async def request_evidence(request:Request,case_id:str,data:EvidenceInput)->dict:
    actor=identity(request)
    async with lock:
        with Session.begin() as s:
            a=get_case(s,case_id);ensure_editable(a);invalidate(s,a,'cam','Evidence request')
            r=EvidenceRequest(case_id=case_id,revision=a.revision,data={'message':data.message,'source':'reviewer'});s.add(r);a.status='needs_evidence';audit(s,case_id,'evidence_requested',actor=actor,message=data.message);s.flush();return serialize(r)
@post('/api/applications/{case_id:str}/evidence-requests/{request_id:str}/resolve')
async def resolve(request:Request,case_id:str,request_id:str,data:EvidenceInput)->dict:
    actor=identity(request)
    async with lock:
        with Session.begin() as s:
            a=get_case(s,case_id);ensure_editable(a);r=s.get(EvidenceRequest,request_id)
            if not r or r.case_id!=case_id or r.data['source']!='reviewer':raise ClientException('Only a current reviewer request can be resolved here',status_code=422)
            r.status='resolved';r.data={**r.data,'resolution':data.message,'resolved_by':actor};invalidate(s,a,'cam','Reviewer evidence resolution');audit(s,case_id,'evidence_resolved',actor=actor,request_id=request_id,message=data.message);return serialize(r)
@get('/api/applications/{case_id:str}/cams',sync_to_thread=True)
def cams(request:Request,case_id:str)->dict:
    identity(request)
    with Session() as s:
        a=get_case(s,case_id);return {'current_revision':a.revision,'items':[serialize(c) for c in case_records(s,CamVersion,case_id)]}
@post('/api/applications/{case_id:str}/review')
async def reviewer(request:Request,case_id:str,data:ReviewInput)->dict:
    actor=identity(request,reviewer=True)
    async with lock:return await asyncio.to_thread(review,case_id,data,actor)
@get('/api/applications/{case_id:str}/audit',sync_to_thread=True)
def audit_events(request:Request,case_id:str,offset:int=0,limit:int=100)->dict:
    identity(request)
    if offset<0 or not 1<=limit<=500:raise ClientException('Invalid pagination',status_code=422)
    with Session() as s:
        get_case(s,case_id);q=select(AuditEvent).where(AuditEvent.case_id==case_id).order_by(AuditEvent.created_at,AuditEvent.id)
        return {'items':[serialize(x) for x in s.scalars(q.offset(offset).limit(limit))],'total':s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.case_id==case_id))}
@get('/api/ledger',sync_to_thread=True)
def ledger(request:Request,offset:int=0,limit:int=50)->dict:
    identity(request)
    if offset<0 or not 1<=limit<=100:raise ClientException('Invalid pagination',status_code=422)
    with Session() as s:return {'items':[serialize(x) for x in s.scalars(select(MockLedgerEntry).order_by(MockLedgerEntry.created_at.desc()).offset(offset).limit(limit))],'total':s.scalar(select(func.count()).select_from(MockLedgerEntry))}

routes=[health,applications,create,workspace,documents_upload,documents,start_run,runs,evidence,analysis,request_evidence,resolve,cams,reviewer,audit_events,ledger]
