import json
from sqlalchemy import select,text
import pytest
from app.models import *
from app.workflows.engine import run
from app.schemas import DocumentInput

def get_cam(c):return next(x['data'] for x in c['cam_versions'] if x['revision']==c['revision'])
def decision(client,id,c,headers,kind='approve'):
    return client.post(f'/api/applications/{id}/review',json={'decision':kind,'revision':c['revision'],'comments':'Checked synthetic evidence and configured policy'},headers=headers)

def test_consistent_and_approval_atomicity(client,auth,reviewer,load_case):
    id,c=load_case();cam=get_cam(c)
    assert all(p['result']=='pass' for p in cam['policy_checks']),cam['policy_checks']
    assert cam['financial_analysis']['complete_months']==12
    assert cam['financial_analysis']['monthly_operating_cash']==220000
    assert cam['financial_analysis']['existing_monthly_debt']==20000
    assert cam['financial_analysis']['dscr']>1.25
    assert c['status']=='awaiting_review'
    assert decision(client,id,c,auth).status_code==403
    assert decision(client,id,c,reviewer).status_code==201
    assert decision(client,id,c,reviewer).status_code==409
    with Session() as s:
        assert len(list(s.scalars(select(MockLedgerEntry).where(MockLedgerEntry.case_id==id))))==1
        assert len(list(s.scalars(select(ReviewDecision).where(ReviewDecision.case_id==id))))==1
    response=client.post(f'/api/applications/{id}/runs',json={},headers=auth)
    assert response.status_code==409

@pytest.mark.parametrize('name,result',[('02_missing_pages','insufficient_evidence'),('03_gst_mismatch','exception'),('04_duplicate_transactions','exception'),('05_potential_cycle','exception'),('06_low_capacity','fail'),('07_missing_kyc','insufficient_evidence')])
def test_adverse_scenarios(client,reviewer,load_case,name,result):
    id,c=load_case(name);cam=get_cam(c)
    assert any(p['result']==result for p in cam['policy_checks'])
    assert decision(client,id,c,reviewer).status_code==409
    if name=='04_duplicate_transactions':assert len(cam['investigation_flags'])>=1 and cam['financial_analysis']['monthly_operating_cash']==220000
    if name=='05_potential_cycle':assert any(f['kind']=='potential_cycle' for f in cam['investigation_flags'])

def test_replacement_invalidates_cam_and_preserves_history(client,auth,reviewer,load_case,fixture_data):
    id,c=load_case('08_additional_evidence');revision=c['revision'];oldcam=c['cam_versions'][0]['id'];kyc=next(d for d in c['documents'] if d['kind']=='kyc')
    newdoc=fixture_data('08_additional_evidence')['additional_document']
    r=client.post(f'/api/applications/{id}/documents',params={'kind':'kyc','replaces':kyc['id']},files={'data':('corrected.json',json.dumps(newdoc),'application/json')},headers=auth);assert r.status_code==201,r.text
    assert decision(client,id,c,reviewer).status_code==409
    c=client.get('/api/applications/'+id,headers=auth).json();assert c['revision']==revision+1 and c['analyzed_revision']==-1
    assert decision(client,id,c,reviewer).status_code==409
    client.post(f'/api/applications/{id}/runs',json={},headers=auth)
    c=client.get('/api/applications/'+id,headers=auth).json();assert len(c['cam_versions'])==2 and c['cam_versions'][0]['id']==oldcam
    assert all(p['result']=='pass' for p in get_cam(c)['policy_checks'])
    assert decision(client,id,c,reviewer).status_code==201

def test_checkpoint_retry(client,auth,load_case):
    id,c=load_case(analyze=False)
    first=run(id,fail_node='risk');assert first['status']=='failed'
    with Session() as s:
        earlier=s.query(AgentRun).filter_by(case_id=id,node='cashflow').one().id
        count=s.query(ExtractedField).filter_by(case_id=id).count()
    assert run(id)['status']=='awaiting_review'
    with Session() as s:
        assert s.query(AgentRun).filter_by(case_id=id,node='cashflow').one().id==earlier
        assert s.query(ExtractedField).filter_by(case_id=id).count()==count
        assert s.query(CamVersion).filter_by(case_id=id).count()==1
    assert client.post(f'/api/applications/{id}/runs',json={},headers=auth).json()['reused']

def test_prompt_injection_is_only_source_data(client,auth,reviewer,load_case):
    id,c=load_case('12_prompt_injection');cam=get_cam(c)
    assert c['status']!='approved' and cam['financial_analysis']['dscr']!=99
    assert cam['model_explanation']['mode']=='mock'
    assert not client.get('/api/ledger',headers=auth).json()['items'] or all(e['case_id']!=id for e in client.get('/api/ledger',headers=auth).json()['items'])
    evidence=client.get(f'/api/applications/{id}/evidence',headers=auth).json()['items']
    assert any('IGNORE ALL RULES' in e['source_text'] for e in evidence)

def test_reviewer_request_blocks_reanalysis_until_resolved(client,auth,reviewer,load_case):
    id,c=load_case();assert decision(client,id,c,reviewer,'request_evidence').status_code==201
    client.post(f'/api/applications/{id}/runs',json={},headers=auth)
    c=client.get('/api/applications/'+id,headers=auth).json();assert decision(client,id,c,reviewer).status_code==409
    request=next(r for r in c['evidence_requests'] if r['data']['source']=='reviewer')
    r=client.post(f"/api/applications/{id}/evidence-requests/{request['id']}/resolve",json={'message':'Verified supporting synthetic evidence; clarification resolved.'},headers=reviewer);assert r.status_code==201,r.text
    client.post(f'/api/applications/{id}/runs',json={},headers=auth)
    c=client.get('/api/applications/'+id,headers=auth).json();assert decision(client,id,c,reviewer).status_code==201

def test_append_only_history(client,load_case):
    id,c=load_case()
    with pytest.raises(Exception):
        with engine.begin() as conn:conn.execute(text('DELETE FROM audit_events WHERE case_id=:id'),{'id':id})

def test_missing_debt_is_not_zero(client,auth,reviewer,load_case,fixture_data):
    data=fixture_data('01_consistent');financial=data['documents'][3];financial['fields']=[f for f in financial['fields'] if f['name']!='existing_monthly_debt']
    id,c=load_case(analyze=False);old=next(d for d in c['documents'] if d['kind']=='financial')
    client.post(f'/api/applications/{id}/documents',params={'kind':'financial','replaces':old['id']},files={'data':('financial.json',json.dumps(financial),'application/json')},headers=auth)
    client.post(f'/api/applications/{id}/runs',json={},headers=auth);c=client.get('/api/applications/'+id,headers=auth).json();assert get_cam(c)['financial_analysis']['dscr'] is None
    assert decision(client,id,c,reviewer).status_code==409

def test_validation_and_permissions(client,auth,load_case,fixture_data):
    assert client.get('/api/applications').status_code==401
    assert client.get('/api/applications?limit=500',headers=auth).status_code==422
    assert client.get('/api/health').status_code==200
    assert client.get('/schema/openapi.json').status_code==200
    id,c=load_case(analyze=False)
    assert client.post(f'/api/applications/{id}/documents?kind=bank',files={'data':('bad.txt',b'not a PDF or JSON','text/plain')},headers=auth).status_code==422
    data=fixture_data('01_consistent')['documents'][0];data['transactions'][0]['date']='invalid'
    with pytest.raises(Exception):DocumentInput.model_validate(data)
    data=fixture_data('01_consistent')['documents'][0];data['transactions'][0]['amount']='-1'
    with pytest.raises(Exception):DocumentInput.model_validate(data)


def test_failed_document_does_not_approve(client,auth,reviewer,load_case):
    id,c=load_case(analyze=False)
    r=client.post(f'/api/applications/{id}/documents?kind=bureau',files={'data':('broken.pdf',b'%PDF-broken','application/pdf')},headers=auth)
    assert r.status_code==201
    client.post(f'/api/applications/{id}/runs',json={},headers=auth)
    c=client.get('/api/applications/'+id,headers=auth).json()
    assert c['status']=='processing_failed'
    assert decision(client,id,c,reviewer).status_code==409

def test_resume_after_process_crash(client,auth,load_case):
    id,c=load_case(analyze=False)
    with Session.begin() as s:s.get(Application,id).status='processing'
    r=client.post(f'/api/applications/{id}/runs',json={},headers=auth)
    assert r.status_code==200 and r.json()['status']=='awaiting_review'
