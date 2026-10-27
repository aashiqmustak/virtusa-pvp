import json
from app.models import Session,DemoChallenge

def otp(client,mobile,purpose='login',headers=None):
    r=client.post('/api/demo/otp/request',json={'mobile':mobile,'purpose':purpose},headers=headers or {});assert r.status_code==201,r.text
    d=r.json();v=client.post('/api/demo/otp/verify',json={'challenge_id':d['challenge_id'],'code':d['demo_otp']});assert v.status_code==201,v.text
    return v.json(),d

def borrower(client,index=1):
    mobile=str(9000000000+index);d,_=otp(client,mobile)
    return {'Authorization':'Bearer '+d['token']},d['profile']

def create(client,index=1,loan='term'):
    h,p=borrower(client,index);kyc,_=otp(client,p['mobile'],'kyc',h)
    r=client.post('/api/borrower/applications',headers=h,json={'kyc_proof':kyc['kyc_proof'],'pan':p['pan'],'dob':p['dob'],'purpose':'Synthetic equipment','requested_amount':1000000,'tenure_months':36,'loan_type':loan,'consents':['kyc','bank','tax','bureau','processing']});assert r.status_code==201,r.text
    id=r.json()['id'];r=client.post(f'/api/borrower/applications/{id}/fetch',json={},headers=h);assert r.status_code==201,r.text
    return id,h,r.json()

def verification(client,id,auth,revision,**kw):
    d={'revision':revision,'channel':'phone','identity_verified':True,'business_verified':True,'purpose_verified':True,'notes':'Synthetic interview completed','market_assessment':'Local synthetic market viable',**kw}
    r=client.post(f'/api/applications/{id}/verification',headers=auth,json=d);assert r.status_code==201,r.text

def analyze(client,id,auth):
    r=client.post(f'/api/applications/{id}/runs',headers=auth,json={});assert r.status_code==200,r.text
    assert r.json()['status']!='failed',r.text
    return client.get(f'/api/applications/{id}',headers=auth).json()

def test_synthetic_happy_path_and_rate_gates(client,auth,reviewer):
    id,h,a=create(client,7)
    assert a['status']=='awaiting_review'
    assert any(x['rule_id']=='HUMAN_VERIFICATION' and x['result']!='pass' for x in a['checks'])
    assert client.post(f'/api/applications/{id}/review',headers=reviewer,json={'revision':a['revision'],'decision':'approve','comments':'Must block'}).status_code==409
    verification(client,id,auth,a['revision']);a=analyze(client,id,auth)
    r=client.post(f'/api/applications/{id}/terms',headers=auth,json={'revision':a['revision'],'amount':1000000,'tenure_months':36,'annual_rate_percent':13.5,'reason':'Demo negotiated reduction'});assert r.status_code==201,r.text
    a=analyze(client,id,auth);cam=next(x['data'] for x in a['cam_versions'] if x['revision']==a['revision']);assert cam['financial_analysis']['annual_rate_percent']==13.5
    assert cam['financial_analysis']['proposed_emi']<34177.63
    payload={'revision':a['revision'],'approve':True,'reason':'Within demo exception authority'}
    assert client.post(f'/api/applications/{id}/rate-decision',headers=auth,json=payload).status_code==403
    assert client.post(f'/api/applications/{id}/rate-decision',headers=reviewer,json=payload).status_code==201
    a=analyze(client,id,auth);payload={'revision':a['revision'],'decision':'approve','comments':'Reviewed current synthetic CAM'}
    assert client.post(f'/api/applications/{id}/review',headers=auth,json=payload).status_code==403
    r=client.post(f'/api/applications/{id}/review',headers=reviewer,json=payload);assert r.status_code==201,r.text
    assert client.post(f'/api/applications/{id}/review',headers=reviewer,json=payload).status_code==409
    tracked=client.get('/api/borrower/applications',headers=h).json()['items'];assert next(x for x in tracked if x['id']==id)['mock_ledger_posted']
    assert client.post(f'/api/borrower/applications/{id}/fetch',headers=h,json={}).status_code==409

def test_borrower_isolation_and_otp_replay(client,auth):
    id,h,a=create(client,13);other,_=borrower(client,14)
    assert client.post(f'/api/borrower/applications/{id}/fetch',headers=other,json={}).status_code==404
    assert client.get('/api/applications',headers=h).status_code==401
    assert client.get('/api/borrower/applications',headers=other).json()['items']==[]
    d,c=otp(client,'9000000015')
    assert client.post('/api/demo/otp/verify',json={'challenge_id':c['challenge_id'],'code':c['demo_otp']}).status_code==422
    h2={'Authorization':'Bearer '+d['token']}
    assert client.post('/api/borrower/logout',headers=h2,json={}).status_code==201
    assert client.get('/api/borrower/applications',headers=h2).status_code==401

def test_missing_gst_can_be_resolved(client,auth):
    id,h,a=create(client,3);assert a['status']=='needs_evidence';assert a['sources']['gst']['status']=='requires_action'
    from app.models import SyntheticProfile
    with Session() as s:doc=next(d for d in s.get(SyntheticProfile,'SYN-0003').data['documents'] if d['kind']=='gst')
    r=client.post(f'/api/borrower/applications/{id}/documents?kind=gst',headers=h,files={'data':('gst.json',json.dumps(doc).encode(),'application/json')});assert r.status_code==201,r.text
    assert r.json()['status']=='awaiting_review'

def test_lap_requires_survey_and_net_property_value(client,auth,reviewer):
    id,h,a=create(client,19,'lap');verification(client,id,auth,a['revision']);a=analyze(client,id,auth)
    assert client.post(f'/api/applications/{id}/review',headers=reviewer,json={'revision':a['revision'],'decision':'approve','comments':'No survey yet'}).status_code==409
    verification(client,id,auth,a['revision'],surveyor='Demo surveyor',survey_reference='SYN-SURVEY-01',property_value=2000000,margin_percent=25,title_clear=True)
    a=analyze(client,id,auth);cam=next(x['data'] for x in a['cam_versions'] if x['revision']==a['revision']);assert all(x['result']=='pass' for x in cam['policy_checks'])

def test_otp_attempt_limit_expiry_and_missing_consent(client):
    r=client.post('/api/demo/otp/request',json={'mobile':'9000000020','purpose':'login'});d=r.json()
    for _ in range(5):assert client.post('/api/demo/otp/verify',json={'challenge_id':d['challenge_id'],'code':'000000' if d['demo_otp']!='000000' else '111111'}).status_code==422
    assert client.post('/api/demo/otp/verify',json={'challenge_id':d['challenge_id'],'code':d['demo_otp']}).status_code==422
    h,p=borrower(client,21);k,_=otp(client,p['mobile'],'kyc',h)
    payload={'kyc_proof':k['kyc_proof'],'pan':p['pan'],'dob':p['dob'],'purpose':'Equipment','requested_amount':1000000,'tenure_months':36,'consents':['kyc']}
    assert client.post('/api/borrower/applications',headers=h,json=payload).status_code==422
    r=client.post('/api/demo/otp/request',json={'mobile':'9000000022','purpose':'login'});d=r.json()
    with Session.begin() as s:
        c=s.get(DemoChallenge,d['challenge_id']);c.data={**c.data,'issued_at':0}
    assert client.post('/api/demo/otp/verify',json={'challenge_id':d['challenge_id'],'code':d['demo_otp']}).status_code==422

import pytest
@pytest.mark.parametrize('index,rule',[(2,'BUREAU'),(4,'DSCR'),(5,'RECONCILIATION'),(6,'INVESTIGATION')])
def test_provider_scenario_gates(client,index,rule):
    id,h,a=create(client,index+24)
    assert a['status']=='awaiting_review'
    assert any(c['rule_id']==rule and c['result']!='pass' for c in a['checks'])

def test_profile_generator_idempotent(client):
    from app.services.integrations.synthetic import seed_profiles
    from app.models import SyntheticProfile
    with Session.begin() as s:seed_profiles(s,500)
    with Session.begin() as s:
        seed_profiles(s,500)
        assert s.query(SyntheticProfile).count()==500
        assert s.get(SyntheticProfile,'SYN-0500').data['synthetic'] is True
    assert len(client.get('/api/demo/profiles').json()['items'])==500
