"""Local synthetic provider. No external network requests or real identities."""
import copy, json
from pathlib import Path
from app.models import SyntheticProfile

PEOPLE=['Aarav Mehta','Ananya Rao','Vikram Shah','Meera Iyer','Rohan Nair','Kavya Menon','Arjun Desai','Nisha Kapoor','Dev Patel','Ishita Bose','Aditya Sen','Priya Varma']
BUSINESSES=['Aarav Precision Works','Bharat Digital Services','Kaveri Textiles','Shakti Components','Annapurna Foods','Vishwakarma Engineering','Narmada Packaging','Srishti Design Studio','Konkan Logistics','Griha Homeware','Deccan Fabrication','Lakshmi Trading']
CITIES=['Mumbai, Maharashtra','Bengaluru, Karnataka','Coimbatore, Tamil Nadu','Ahmedabad, Gujarat','Kochi, Kerala','Pune, Maharashtra','Vadodara, Gujarat','Chennai, Tamil Nadu','Mangaluru, Karnataka','Jaipur, Rajasthan','Hyderabad, Telangana','Kolkata, West Bengal']
def indian_profile(i):
    return {'name':PEOPLE[(i-1)%12], 'business':BUSINESSES[(i-1)%12]+(f' · {(i-1)//12+1}' if i>12 else ''), 'location':CITIES[(i-1)%12]}

SCENARIOS=['consistent','low_bureau','missing_gst','low_capacity','gst_mismatch','balance_drop']
def seed_profiles(s,count=100):
    if not 100<=count<=500: raise ValueError('Profile count must be between 100 and 500')
    root=Path(__file__).resolve().parents[4]/'fixtures'/'synthetic_cases'
    base=json.loads((root/'01_consistent.json').read_text())
    for i in range(1,count+1):
        pid=f'SYN-{i:04d}'
        existing=s.get(SyntheticProfile,pid)
        if existing:
            if existing.data.get('name','').startswith('Synthetic Owner'):
                d=copy.deepcopy(existing.data);d.update(indian_profile(i))
                for doc in d.get('documents',[]):
                    for f in doc.get('fields',[]):
                        if f['name']=='legal_name':f.update(value=d['name'],source_text='Applicant name: '+d['name'])
                existing.data=d
            continue
        scenario=SCENARIOS[(i-1)%len(SCENARIOS)]
        docs=copy.deepcopy(base['documents']); name=indian_profile(i)['name']
        for d in docs:
            for f in d.get('fields',[]):
                if f['name']=='legal_name':f.update(value=name,source_text='Synthetic KYC name: '+name)
                if f['name']=='tax_id':f.update(value=f'DEMOPAN{i:04d}',source_text=f'Synthetic PAN DEMOPAN{i:04d}')
                if scenario=='gst_mismatch' and f['name']=='gst_turnover':f.update(value='9000000',source_text='Synthetic declared GST turnover INR 9000000')
            for t in d.get('transactions',[]):
                if scenario=='low_capacity' and t['category']=='operating' and t['direction']=='debit':t.update(amount='495000',source_text='Synthetic operating expense INR 495000')
            if scenario=='balance_drop' and d['kind']=='bank':
                d['transactions'][0]['balance']='100000';d['transactions'][1]['balance']='50000'
        s.add(SyntheticProfile(id=pid,mobile=str(9000000000+i),data={'synthetic':True,'pan':f'DEMOPAN{i:04d}','name':name,'dob':'1988-01-15','business':indian_profile(i)['business'],'location':indian_profile(i)['location'],'sector':'manufacturing' if i%2 else 'services','udyam':f'DEMO-UDYAM-{i:04d}','gstin':f'DEMO-GST-{i:04d}','scenario':scenario,'annual_turnover':6000000,'investment_inr':1000000,'bureau':{'score':650 if scenario=='low_bureau' else 760,'monthly_debt':20000,'credit_utilization_percent':25,'source':'synthetic-bureau-v1'},'documents':docs}))

def provider_records(profile,include_missing=False):
    """Deterministic provider records; repeated fetches return identical bytes."""
    return [d for d in profile.data['documents'] if include_missing or not (profile.data['scenario']=='missing_gst' and d['kind']=='gst')]

TOOL_REGISTRY={
 'fetch_synthetic_case':{'input':{'profile_id':'string','consent_id':'string'},'output':'validated DocumentInput[]','provider':'local-synthetic-v1','network':False},
 'calculate_financials':{'input':'normalized evidence and terms','output':'CashFlowResult','deterministic':True},
 'post_mock_cbs':{'input':'approved current CAM','output':'unique mock ledger entry','human_approval_required':True},
}
