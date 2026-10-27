import hashlib
from pathlib import Path
from sqlalchemy import select, update
from litestar.exceptions import NotFoundException,ClientException
from app.models import *
from app.workflows.engine import case_records,invalidate
from app.schemas import DocumentInput
from app.config import settings
from app.services.policy.engine import DEFAULT_POLICY

def get_case(s,id):
    a=s.get(Application,id)
    if not a:raise NotFoundException('Case not found')
    return a

def ensure_editable(a):
    if a.status in ['approved','rejected','processing']:raise ClientException('Case is finalized or busy',status_code=409)

def serialize(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns if c.name!='path'}

def upload(case_id,name,kind,raw,replaces=None):
    if len(raw)>settings.max_upload or not raw:raise ClientException('Empty file or file exceeds 10 MiB',status_code=413)
    is_pdf=raw.startswith(b'%PDF-')
    if not is_pdf:
        try:DocumentInput.model_validate_json(raw)
        except Exception as e:raise ClientException('Invalid synthetic JSON document: '+str(e)[:300],status_code=422)
    digest=hashlib.sha256(raw).hexdigest()
    settings.storage.mkdir(parents=True,exist_ok=True)
    with Session.begin() as s:
        a=s.scalar(select(Application).where(Application.id==case_id).with_for_update());
        if not a:raise NotFoundException('Case not found')
        ensure_editable(a)
        existing=s.query(Document).filter_by(case_id=case_id,sha256=digest).first()
        if existing:raise ClientException('Duplicate document',status_code=409)
        if kind not in ['bank','gst','itr','financial','kyc','bureau']:raise ClientException('Invalid document kind',status_code=422)
        if replaces:
            previous=s.get(Document,replaces)
            if not previous or previous.case_id!=case_id or previous.kind!=kind or previous.status=='superseded':raise ClientException('Invalid replacement target',status_code=422)
            previous.status='superseded'
        id=uid();path=settings.storage/(id+('.pdf' if is_pdf else '.json'));path.write_bytes(raw);path.chmod(0o600)
        try:
            doc=Document(id=id,case_id=case_id,name=Path(name).name[:160],path=str(path),kind=kind,sha256=digest)
            s.add(doc);invalidate(s,a,'documents','Evidence uploaded/replaced')
            audit(s,case_id,'document_uploaded',document_id=id,sha256=digest,replaces=replaces)
            s.flush();out=serialize(doc)
        except Exception:path.unlink(missing_ok=True);raise
    return out

def review(case_id,decision,reviewer):
    with Session.begin() as s:
        a=s.scalar(select(Application).where(Application.id==case_id).with_for_update())
        if not a:raise NotFoundException('Case not found')
        # Compare-and-set protects SQLite demo too; PostgreSQL row lock serializes review/upload.
        if a.revision!=decision.revision:raise ClientException('Stale review revision',status_code=409)
        if a.status in ['approved','rejected','processing']:raise ClientException('Finalized or processing case',status_code=409)
        cam=s.query(CamVersion).filter_by(case_id=case_id,revision=a.revision).first()
        if decision.decision=='approve':
            import time
            if any(v.status in ['pending','active'] and v.expires_at>time.time() for v in case_records(s,VoiceSession,case_id)):raise ClientException('Finish or stop the voice interview before approval',status_code=409)
            from app.services.journey import guard_approval
            guard_approval(a.data,DEFAULT_POLICY)
            if any(r.status=='open' and r.data.get('source')=='reviewer' for r in case_records(s,EvidenceRequest,case_id)):raise ClientException('Open reviewer requests block approval',status_code=409)
            if a.analyzed_revision!=a.revision or not cam:raise ClientException('Current analysis and CAM required',status_code=409)
            if cam.data['policy_version']!=DEFAULT_POLICY['version']:raise ClientException('Policy changed; re-run analysis',status_code=409)
            if not all(c['result']=='pass' for c in cam.data['policy_checks']):raise ClientException('Unresolved evidence, investigation or policy failures block approval',status_code=409)
        before=a.status;target={'approve':'approved','reject':'rejected','request_evidence':'needs_evidence'}[decision.decision]
        changed=s.execute(update(Application).where(Application.id==case_id,Application.status==before,Application.revision==decision.revision).values(status=target)).rowcount
        if changed!=1:raise ClientException('Concurrent decision; reload',status_code=409)
        record=ReviewDecision(id=uid(),case_id=case_id,reviewer_id=reviewer,revision=a.revision,data=decision.model_dump())
        s.add(record);s.flush()
        if decision.decision=='approve':s.add(MockLedgerEntry(case_id=case_id,decision_id=record.id,data={'mock_only':True,'terms':cam.data['proposal'],'cam_id':cam.id,'reviewer_id':reviewer}))
        if decision.decision=='request_evidence':
            s.add(EvidenceRequest(case_id=case_id,revision=a.revision,data={'message':decision.comments,'source':'reviewer'}))
            # New analysis cannot silently close an unresolved reviewer request.
            invalidate(s,a,'cam','Reviewer requested more evidence')
            a.status='needs_evidence'
        audit(s,case_id,'review_decision',reviewer_id=reviewer,decision=decision.decision,revision=decision.revision,comments=decision.comments)
        return serialize(record)
