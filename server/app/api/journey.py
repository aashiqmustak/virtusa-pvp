import asyncio,hashlib,json,secrets,time
from typing import Annotated
from litestar import get,post,Request
from litestar.datastructures import UploadFile
from litestar.params import Body
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException,NotAuthorizedException,NotFoundException
from app.models import *
from app.schemas import EvidenceInput
from app.schemas.journey import OTPRequest,OTPVerify,BorrowerApplication,Verification,Terms,RateDecision
from app.security.auth import identity
from app.api.routes import lock
from app.services.cases import get_case,ensure_editable,serialize,upload
from app.services.integrations.synthetic import provider_records,TOOL_REGISTRY
from app.services.journey import REQUIRED_CONSENTS,update
from app.workflows.engine import run,invalidate,case_records
from app.services.policy.engine import DEFAULT_POLICY

def digest(v):return hashlib.sha256(v.encode()).hexdigest()
def borrower(request,s):
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    session=s.query(BorrowerSession).filter_by(token_hash=digest(token)).first()
    if not session or session.expires_at<time.time():raise NotAuthorizedException('Borrower session expired; sign in again')
    return s.get(SyntheticProfile,session.profile_id)
def owned(s,id,p):
    a=get_case(s,id)
    if a.data.get('journey',{}).get('profile_id')!=p.id:raise NotFoundException('Application not found')
    return a
def public_profile(p):return {'id':p.id,'mobile':p.mobile,**{k:v for k,v in p.data.items() if k not in ['documents','bureau']}}
def borrower_case(s,a):
    j=a.data['journey'];cam=s.query(CamVersion).filter_by(case_id=a.id,revision=a.revision).first()
    sources={k:dict(v) for k,v in j.get('sources',{}).items()}
    for d in case_records(s,Document,a.id):
        if d.status=='parsed' and d.kind in sources and sources[d.kind]['status']=='requires_action':sources[d.kind]={**sources[d.kind],'status':'fetched','evidence_id':d.id,'message':'Missing source supplied as additional synthetic evidence'}
    requests=[serialize(r) for r in case_records(s,EvidenceRequest,a.id) if r.status=='open' and (r.data.get('source')=='reviewer' or r.revision==a.revision)]
    return {'id':a.id,'status':a.status,'revision':a.revision,'data':{k:v for k,v in a.data.items() if k!='journey'},'sources':sources,'loan_type':j['loan_type'],'requests':requests,'documents':[serialize(d) for d in case_records(s,Document,a.id)],'checks':cam.data['policy_checks'] if cam else [],'proposal':cam.data['proposal'] if cam else None,'verification_complete':bool(j.get('verification')),'mock_ledger_posted':s.query(MockLedgerEntry).filter_by(case_id=a.id).first() is not None}

@get('/api/demo/profiles',sync_to_thread=True)
def profiles()->dict:
    with Session() as s:return {'synthetic_only':True,'items':[public_profile(p) for p in s.query(SyntheticProfile).order_by(SyntheticProfile.id)]}
@get('/api/me',sync_to_thread=True)
def me(request:Request)->dict:
    actor=identity(request)
    return {'id':actor,'role':'manager' if actor=='reviewer-local' else 'credit_officer'}
@post('/api/demo/otp/request')
async def otp_request(request:Request,data:OTPRequest)->dict:
    async with lock:
        with Session.begin() as s:
            p=s.query(SyntheticProfile).filter_by(mobile=data.mobile).first()
            if not p:raise ClientException('Choose a synthetic profile mobile from the demo directory',status_code=422)
            if data.purpose=='kyc' and borrower(request,s).id!=p.id:raise NotAuthorizedException('KYC must match signed-in profile')
            previous=s.query(DemoChallenge).filter_by(mobile=data.mobile).all()
            if sum(x.data['issued_at']>time.time()-60 for x in previous)>=5:raise ClientException('Too many OTP requests; retry after one minute',status_code=429)
            code=f'{secrets.randbelow(1000000):06d}';challenge=DemoChallenge(id=uid(),mobile=data.mobile,data={'code_hash':digest(code),'purpose':data.purpose,'issued_at':time.time(),'attempts':0,'used':False})
            s.add(challenge)
            return {'challenge_id':challenge.id,'demo_otp':code,'expires_in':300,'message':'SIMULATION ONLY — no SMS sent'}
@post('/api/demo/otp/verify')
async def otp_verify(data:OTPVerify)->dict:
    error=None;result={}
    async with lock:
        with Session.begin() as s:
            c=s.get(DemoChallenge,data.challenge_id)
            if not c or c.data['used'] or c.data['issued_at']<time.time()-300 or c.data['attempts']>=5:error='OTP expired, consumed or attempts exhausted'
            elif not secrets.compare_digest(c.data['code_hash'],digest(data.code)):
                c.data={**c.data,'attempts':c.data['attempts']+1};error='Incorrect OTP'
            else:
                c.data={**c.data,'used':True}
                if c.data['purpose']=='kyc':result={'kyc_proof':c.id,'synthetic_verified':True}
                else:
                    p=s.query(SyntheticProfile).filter_by(mobile=c.mobile).one();token=secrets.token_urlsafe(32)
                    s.add(BorrowerSession(token_hash=digest(token),profile_id=p.id,expires_at=time.time()+28800));result={'token':token,'profile':public_profile(p),'expires_in':28800}
    if error:raise ClientException(error,status_code=422)
    return result
@get('/api/borrower/applications',sync_to_thread=True)
def my_cases(request:Request)->dict:
    with Session() as s:
        p=borrower(request,s)
        return {'profile':public_profile(p),'items':[borrower_case(s,a) for a in s.query(Application).order_by(Application.created_at.desc()) if a.data.get('journey',{}).get('profile_id')==p.id]}
@post('/api/borrower/logout')
async def signout(request:Request)->dict:
    async with lock:
        with Session.begin() as s:
            borrower(request,s);s.query(BorrowerSession).filter_by(token_hash=digest(request.headers.get('Authorization','').removeprefix('Bearer '))).delete()
    return {'signed_out':True}
@post('/api/borrower/applications')
async def apply(request:Request,data:BorrowerApplication)->dict:
    async with lock:
        with Session.begin() as s:
            p=borrower(request,s);proof=s.get(DemoChallenge,data.kyc_proof)
            if not proof or not proof.data['used'] or proof.data['purpose']!='kyc' or proof.mobile!=p.mobile or proof.data['issued_at']<time.time()-1800 or proof.data.get('application_id'):raise ClientException('Complete a fresh synthetic KYC OTP verification',status_code=422)
            if data.pan!=p.data['pan'] or data.dob!=p.data['dob']:raise ClientException('PAN/DOB do not match this synthetic profile',status_code=422)
            if not REQUIRED_CONSENTS<=set(data.consents):raise ClientException('All five consents are required',status_code=422)
            a=Application(id=uid(),status='draft',revision=0,data={'synthetic':True,'applicant':p.data['name'],'business':p.data['business'],'purpose':data.purpose,'requested_amount':str(data.requested_amount),'tenure_months':data.tenure_months,'journey':{'profile_id':p.id,'pan':data.pan,'loan_type':data.loan_type,'kyc_proof':proof.id,'consents':data.consents,'consent_id':uid(),'consent_at':now(),'rate_exception':{'status':'not_required'},'sources':{},'original_request':{'amount':str(data.requested_amount),'tenure_months':data.tenure_months}}})
            proof.data={**proof.data,'application_id':a.id};s.add(a);s.flush();audit(s,a.id,'borrower_application_submitted',profile_id=p.id,consents=data.consents,consent_id=a.data['journey']['consent_id']);return borrower_case(s,a)

@post('/api/borrower/applications/{case_id:str}/fetch')
async def fetch_data(request:Request,case_id:str)->dict:
    async with lock:
        with Session() as s:
            p=borrower(request,s);a=owned(s,case_id,p);ensure_editable(a)
            if not REQUIRED_CONSENTS<=set(a.data['journey'].get('consents',[])):raise ClientException('Consent required',status_code=422)
            docs=provider_records(p);pdata=p.data.copy();profile_id=p.id
        for d in docs:
            raw=json.dumps(d,sort_keys=True).encode()
            with Session() as s:
                # Fetch retry does not re-upload or supersede evidence supplied by a human.
                if any(x.kind==d['kind'] and x.status!='superseded' for x in case_records(s,Document,case_id)):continue
            await asyncio.to_thread(upload,case_id,'synthetic-'+d['kind']+'.json',d['kind'],raw)
        with Session.begin() as s:
            a=get_case(s,case_id);j=dict(a.data['journey']);sources={}
            for kind in ['bank','gst','itr','financial','kyc']:
                d=next((x for x in case_records(s,Document,case_id) if x.kind==kind and x.status!='superseded'),None)
                sources[kind]={'status':'fetched' if d else 'requires_action','provider':'local-synthetic-v1','fetched_at':now(),'consent_id':j['consent_id'],'evidence_id':d.id if d else None,'message':'Synthetic record available' if d else 'Provider fixture has no GST record. Upload the missing synthetic GST evidence.'}
            for kind in ['bureau','udyam']:
                sources[kind]={'status':'fetched','provider':'local-synthetic-v1','fetched_at':now(),'consent_id':j['consent_id'],'evidence_id':profile_id+':'+kind}
            j.update(sources=sources,bureau=pdata['bureau'],udyam=pdata['udyam'],gstin=pdata['gstin'],sector=pdata['sector'],classification={'category':'Micro','basis':'Synthetic provider fixture; not official MSME certification','annual_turnover':pdata.get('annual_turnover',6000000),'investment_inr':pdata.get('investment_inr',1000000)})
            update(s,a,j,profile_id,'synthetic_data_fetched')
        await asyncio.to_thread(run,case_id)
        with Session() as s:return borrower_case(s,get_case(s,case_id))
@post('/api/borrower/applications/{case_id:str}/documents')
async def supply(request:Request,case_id:str,data:Annotated[UploadFile,Body(media_type=RequestEncodingType.MULTI_PART)],kind:str,replaces:str|None=None)->dict:
    raw=await data.read(settings.max_upload+1)
    async with lock:
        with Session() as s:owned(s,case_id,borrower(request,s))
        await asyncio.to_thread(upload,case_id,data.filename or 'evidence',kind,raw,replaces)
        await asyncio.to_thread(run,case_id)
        with Session() as s:return borrower_case(s,get_case(s,case_id))
@post('/api/borrower/applications/{case_id:str}/responses')
async def respond(request:Request,case_id:str,data:EvidenceInput)->dict:
    async with lock:
        with Session.begin() as s:
            p=borrower(request,s);a=owned(s,case_id,p);ensure_editable(a)
            audit(s,case_id,'borrower_clarification',profile_id=p.id,message=data.message)
    return {'recorded':True,'message':'Recorded for credit team review; open requests remain until staff resolve them.'}
@post('/api/applications/{case_id:str}/verification')
async def verify_human(request:Request,case_id:str,data:Verification)->dict:
    actor=identity(request)
    async with lock:
        with Session.begin() as s:
            a=get_case(s,case_id);ensure_editable(a)
            if 'journey' not in a.data or a.revision!=data.revision:raise ClientException('Journey case and current revision required',status_code=409)
            j=dict(a.data['journey']);j['verification']={**data.model_dump(mode='json'),'actor':actor,'recorded_at':now(),'simulation':True}
            invalidate(s,a,'cam','Human verification updated');update(s,a,j,actor,'human_verification_recorded')
    return {'saved':True,'rerun_required':True}
@post('/api/applications/{case_id:str}/terms')
async def terms(request:Request,case_id:str,data:Terms)->dict:
    actor=identity(request)
    async with lock:
        with Session.begin() as s:
            a=get_case(s,case_id);ensure_editable(a)
            if 'journey' not in a.data or a.revision!=data.revision:raise ClientException('Journey case and current revision required',status_code=409)
            base=DEFAULT_POLICY['annual_rate_percent'];rate=float(data.annual_rate_percent)
            if not max(0,base-1)<=rate<=base+5:raise ClientException('Demo hard rate bounds: base minus 1 to base plus 5 percentage points',status_code=422)
            j=dict(a.data['journey']);j['rate_exception']={'status':'pending' if rate!=base else 'not_required','base_rate':base,'proposed_rate':rate,'reason':data.reason,'proposed_by':actor}
            a.data={**a.data,'requested_amount':str(data.amount),'tenure_months':data.tenure_months,'annual_rate_percent':rate}
            invalidate(s,a,'cashflow','Loan terms changed');update(s,a,j,actor,'loan_terms_proposed')
    return {'saved':True,'rerun_required':True}
@post('/api/applications/{case_id:str}/rate-decision')
async def rate_decision(request:Request,case_id:str,data:RateDecision)->dict:
    actor=identity(request,reviewer=True)
    async with lock:
        with Session.begin() as s:
            a=get_case(s,case_id);ensure_editable(a);j=dict(a.data.get('journey',{}))
            if a.revision!=data.revision or j.get('rate_exception',{}).get('status')!='pending':raise ClientException('Current pending rate exception required',status_code=409)
            j['rate_exception']={**j['rate_exception'],'status':'approved' if data.approve else 'rejected','decided_by':actor,'decision_reason':data.reason,'decided_at':now()}
            invalidate(s,a,'cam','Manager rate decision');update(s,a,j,actor,'rate_exception_decided')
    return {'saved':True,'rerun_required':True}

routes=[profiles,me,otp_request,otp_verify,my_cases,signout,apply,fetch_data,supply,respond,verify_human,terms,rate_decision]
