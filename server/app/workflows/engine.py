from sqlalchemy import select, delete
from app.models import *
from app.config import settings
from app.schemas.agents import validate_node
from app.services.documents.parser import parse_isolated as parse
from app.services.reconciliation.engine import reconcile
from app.services.financial.analysis import calculate
from app.services.fraud.analysis import investigate
from app.services.policy.engine import evaluate,DEFAULT_POLICY
from app.services.cam.generator import generate
from app.agents.specialists import specialist,explain

NODES=['documents','reconciliation','cashflow','fraud','risk','policy','structure','cam']

def case_records(s,cls,case_id,revision=None):
    q=select(cls).where(cls.case_id==case_id)
    if revision is not None:q=q.where(cls.revision==revision)
    return list(s.scalars(q.order_by(cls.created_at,cls.id)))

def extract(s,case_id):
    docs=[d for d in case_records(s,Document,case_id) if d.status!='superseded']
    gaps=[]; errors=[]
    for doc in docs:
        if doc.status=='parsed':continue
        try:
            data=parse(doc.path)
            if data['kind']!=doc.kind:raise ValueError('Declared type differs from document type')
            s.execute(delete(ExtractedField).where(ExtractedField.document_id==doc.id));s.execute(delete(Transaction).where(Transaction.document_id==doc.id))
            for f in data['fields']:
                id=uid();s.add(ExtractedField(id=id,case_id=case_id,document_id=doc.id,data={**f,'evidence_id':id,'document_id':doc.id,'document_name':doc.name,'classification':'extracted_fact'}))
            for t in data['transactions']:
                id=uid();s.add(Transaction(id=id,case_id=case_id,document_id=doc.id,data={**t,'evidence_id':id,'document_id':doc.id,'document_name':doc.name,'classification':'extracted_fact'}))
            doc.data={k:v for k,v in data.items() if k not in ['fields','transactions']};doc.status='parsed'
        except Exception as e:
            doc.status='failed';doc.data={'error':str(e)[:500]};errors.append({'document_id':doc.id,'error':str(e)[:500]})
    s.flush()
    gaps.extend('Unreadable document: '+e['document_id'] for e in errors)
    active=[d for d in docs if d.status=='parsed'];ids=[d.id for d in active]
    fields=[x.data for x in case_records(s,ExtractedField,case_id) if x.document_id in ids]
    txs=[x.data for x in case_records(s,Transaction,case_id) if any(d.id==x.document_id and d.kind=='bank' for d in active)]
    for kind in ['bank','gst','itr','financial','kyc']:
        chosen=[d for d in active if d.kind==kind]
        if len(chosen)!=1:gaps.append(f'Exactly one current readable {kind} document required; use explicit replacement for corrections.')
        for d in chosen:
            if len(d.data['pages_present'])!=d.data['expected_pages']:gaps.append(f'{d.name}: missing pages')
    for name in ['legal_name','tax_id','existing_monthly_debt','gst_turnover','itr_turnover','financial_turnover']:
        fs=[f for f in fields if f['name']==name]
        expected={'legal_name':'kyc','tax_id':'kyc','existing_monthly_debt':'financial','gst_turnover':'gst','itr_turnover':'itr','financial_turnover':'financial'}[name]
        valid=[f for f in fs if any(d.id==f['document_id'] and d.kind==expected for d in active)]
        if len(valid)!=1:gaps.append(f'Missing or ambiguous {name} in {expected} evidence')
        # Exclude cross-document mislabeled fields from downstream calculations.
        fields=[f for f in fields if f['name']!=name or f in valid]
    names=[f for f in fields if f['name']=='legal_name']
    applicant=s.get(Application,case_id).data['applicant']
    if len(names)==1 and str(names[0]['value']).casefold()!=applicant.casefold():gaps.append('KYC legal name differs from applicant; clarification required')
    if not txs:gaps.append('No readable bank transactions')
    if any(t['category']=='unknown' for t in txs):gaps.append('Unclassified transactions need clarification')
    banks=[d for d in active if d.kind=='bank']
    bank=banks[0].data if len(banks)==1 else None
    return {'gaps':gaps,'errors':errors,'fields':fields,'transactions':txs,'bank':bank,'agent':specialist('documents',[{'message':g} for g in gaps],[f['evidence_id'] for f in fields],'insufficient_data' if gaps else 'complete')}

def run(case_id,fail_node=None):
    # Persistent sequential DAG. Every completed node commits a checkpoint; retries reuse it.
    with Session.begin() as s:
        a=s.get(Application,case_id)
        if not a:raise ValueError('Case not found')
        revision=a.revision; app=a.data
        if a.status in ['approved','rejected']:raise ValueError('Finalized case cannot be analyzed')
        a.status='processing';policy=s.query(PolicyRule).filter_by(version=DEFAULT_POLICY['version']).one().data
        audit(s,case_id,'analysis_started',revision=revision,policy_version=policy['version'])
    policy={**policy,'annual_rate_percent':app.get('annual_rate_percent',policy['annual_rate_percent'])}
    state={}
    for node in NODES:
        try:
            with Session.begin() as s:
                checkpoint=s.query(AgentRun).filter_by(case_id=case_id,revision=revision,node=node).first()
                if checkpoint and checkpoint.status=='complete':state[node]=checkpoint.data['result'];continue
                if not checkpoint:checkpoint=AgentRun(case_id=case_id,revision=revision,node=node,status='running');s.add(checkpoint)
                checkpoint.status='running';s.flush()
                if fail_node==node:raise RuntimeError('Injected test failure')
                if node=='documents':result=extract(s,case_id)
                elif node=='reconciliation':result=reconcile(state['documents']['fields'],state['documents']['transactions'],state['documents']['bank'],policy)
                elif node=='cashflow':result=calculate(state['documents']['fields'],state['documents']['transactions'],state['documents']['bank'],app,policy,state['reconciliation'])
                elif node=='fraud':result=investigate(state['documents']['transactions'])
                elif node=='risk':
                    ms=state['cashflow']['monthly']; cash=[r['operating_credits']-r['operating_debits'] for r in ms.values()]
                    result={'outcome':'manual_review' if state['fraud'] or state['documents']['gaps'] else 'rules_only','no_predictive_score':True,'evidence_ids':state['cashflow']['evidence_ids'],'monthly_cash_range':{'min':min(cash) if cash else None,'max':max(cash) if cash else None},'leverage':'insufficient evidence; balance-sheet liabilities/equity not mapped','findings':state['fraud']+[{'kind':'evidence_gap','message':g} for g in state['documents']['gaps']]}
                elif node=='policy':result=evaluate(state['cashflow'],state['reconciliation'],state['fraud'],state['documents']['gaps'],float(app['requested_amount']),app['tenure_months'],policy)
                elif node=='structure':
                    m=state['cashflow'];ready=all(p['result']=='pass' for p in state['policy'])
                    result={'status':'proposal_requires_review' if ready else 'blocked_pending_evidence_or_policy','requested_principal':app['requested_amount'],'capacity_limit':m['eligible_principal'],'proposed_principal':float(app['requested_amount']) if ready else None,'tenure_months':app['tenure_months'],'nominal_annual_rate_percent':policy['annual_rate_percent'],'monthly_installment':m['proposed_emi'],'rationale':'Requested terms meet configured demo rules.' if ready else 'No approvable terms while evidence, investigation or policy outcomes remain unresolved.','evidence_ids':m['evidence_ids']}
                elif node=='cam':
                    from app.services.journey import checks as journey_checks
                    state['policy']=state['policy']+journey_checks(app,policy)
                    if not all(p['result']=='pass' for p in state['policy']):state['structure']={**state['structure'],'status':'blocked_pending_evidence_or_policy','proposed_principal':None}
                    open_requests=[r for r in case_records(s,EvidenceRequest,case_id) if r.status=='open' and r.data.get('source')=='reviewer']
                    if open_requests:
                        state['policy']=state['policy']+[{'rule_id':'REVIEWER_EVIDENCE','rule_version':policy['version'],'inputs':{'requests':[r.id for r in open_requests]},'result':'insufficient_evidence','reason':'Unresolved reviewer evidence request','evidence_ids':[]}]
                        state['structure']={**state['structure'],'status':'blocked_pending_evidence_or_policy','proposed_principal':None}
                    result=generate(app,revision,state,policy)
                    result['voice_interviews']=[{'id':v.id,'status':v.status,'revision':v.revision,**v.data} for v in case_records(s,VoiceSession,case_id)]
                    result['clarifications']=[{'request_id':r.id,'status':r.status,**r.data} for r in case_records(s,EvidenceRequest,case_id) if r.data.get('source')=='reviewer']
                    result['model_explanation']=explain({'policy':state['policy'],'evidence_ids':state['cashflow']['evidence_ids'][:30]})
                    s.add(CamVersion(case_id=case_id,revision=revision,data=result))
                result=validate_node(node,result)
                state[node]=result
                checkpoint.status='complete';checkpoint.data={'result':result,'agent_version':'1.0','model_mode':settings.llm_mode,'model':settings.ollama_model or None,'policy_version':policy['version'],'finished_at':now(),'agent':specialist(node if node!='reconciliation' else 'Reconciliation',[],state.get('cashflow',{}).get('evidence_ids',[]),'insufficient_data' if node=='documents' and result['gaps'] else 'complete')}
                if node in ['reconciliation','cashflow','fraud','policy']:
                    cls={'reconciliation':ReconciliationFinding,'cashflow':FinancialMetric,'fraud':RiskFlag,'policy':PolicyEvaluation}[node]
                    for item in result if isinstance(result,list) else [result]:s.add(cls(case_id=case_id,revision=revision,data=item))
                if node=='documents':
                    for gap in result['gaps']:s.add(EvidenceRequest(case_id=case_id,revision=revision,data={'message':gap,'source':'document_validation'}))
                audit(s,case_id,'node_completed',node=node,revision=revision)
        except Exception as e:
            with Session.begin() as s:
                checkpoint=s.query(AgentRun).filter_by(case_id=case_id,revision=revision,node=node).first()
                if not checkpoint:checkpoint=AgentRun(case_id=case_id,revision=revision,node=node,status='failed');s.add(checkpoint)
                checkpoint.status='failed';checkpoint.data={'error_type':type(e).__name__,'error':str(e)[:500]}
                s.get(Application,case_id).status='failed';audit(s,case_id,'node_failed',node=node,revision=revision,error_type=type(e).__name__)
            return {'status':'failed','node':node,'revision':revision}
    with Session.begin() as s:
        a=s.get(Application,case_id);a.analyzed_revision=revision
        a.status='processing_failed' if state['documents']['errors'] else ('needs_evidence' if state['documents']['gaps'] or any(p['rule_id']=='REVIEWER_EVIDENCE' for p in state['cam']['policy_checks']) else 'awaiting_review')
        audit(s,case_id,'analysis_completed',revision=revision,status=a.status)
    return {'status':a.status,'revision':revision}

# An evidence replacement invalidates extraction and all descendants. Reviewer text
# invalidates CAM only; calculations are copied as unchanged typed checkpoints.
def invalidate(s,app,start,reason):
    old=app.revision;app.revision+=1;app.analyzed_revision=-1;app.status='draft'
    cutoff=NODES.index(start)
    for node in NODES[:cutoff]:
        prior=s.query(AgentRun).filter_by(case_id=app.id,revision=old,node=node,status='complete').first()
        if prior:s.add(AgentRun(case_id=app.id,revision=app.revision,node=node,status='complete',data=prior.data))
    audit(s,app.id,'results_invalidated',previous_revision=old,revision=app.revision,from_node=start,reason=reason)
