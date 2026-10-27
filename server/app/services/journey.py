"""Synthetic journey gates. These are demo product rules, not bank policy."""
from decimal import Decimal
from litestar.exceptions import ClientException
from app.models import audit,now

REQUIRED_CONSENTS={'kyc','bank','tax','bureau','processing'}
def checks(app,policy):
    j=app.get('journey')
    if not j:return []
    source=j.get('sources',{});v=j.get('verification',{});b=j.get('bureau',{})
    from app.services.policy.engine import DEFAULT_POLICY
    base=DEFAULT_POLICY['annual_rate_percent'];rate=app.get('annual_rate_percent',base);ex=j.get('rate_exception',{})
    rate_ok=(rate==base and ex.get('status')=='not_required') or (ex.get('status')=='approved' and ex.get('base_rate')==base and ex.get('proposed_rate')==rate)
    def check(id,ok,reason,inputs):return {'rule_id':id,'rule_version':policy['version']+'-journey-v1','inputs':inputs,'result':'pass' if ok else 'insufficient_evidence','reason':reason,'evidence_ids':[x['evidence_id'] for x in source.values() if x.get('evidence_id')]}
    rows=[check('CONSENT',REQUIRED_CONSENTS<=set(j.get('consents',[])),'All five synthetic data consents required.',{'consent_id':j.get('consent_id')}),
      check('BUSINESS_VERIFICATION',bool(j.get('udyam')) and bool(j.get('gstin')),'Synthetic Udyam and GST verification required.',{'udyam':j.get('udyam'),'gstin':j.get('gstin')}),
      check('BUREAU',b.get('score',0)>=700,'Demo bureau threshold 700; a lower score requires policy review, not an automatic rate workaround.',b),
      check('HUMAN_VERIFICATION',all(v.get(k) for k in ['identity_verified','business_verified','purpose_verified']) and bool(v.get('market_assessment')),'Credit officer must record identity, business, purpose and market verification.',v),
      check('RATE_BOUNDS',max(0,base-1)<=rate<=base+5,'Non-overridable demo rate interval: base minus 1 through base plus 5 percentage points.',{'base':base,'rate':rate}),
      check('RATE_EXCEPTION',rate_ok,'Any change from the base rate needs manager approval.',j.get('rate_exception',{}))]
    if j['loan_type'] in ['lap','construction']:
        margin=Decimal(str(v.get('margin_percent',0)));value=Decimal(str(v.get('property_value',0)))
        ok=bool(v.get('surveyor') and v.get('survey_reference') and v.get('title_clear')) and 10<=margin<=40 and value>0 and Decimal(str(app['requested_amount']))<=value*(1-margin/100)
        rows.append(check('PROPERTY',ok,'Demo LAP/construction gate: survey reference, clear title, 10–40% margin and loan within net property value.',{'surveyor':v.get('surveyor'),'survey_reference':v.get('survey_reference'),'property_value':str(value),'margin_percent':str(margin),'title_clear':v.get('title_clear')}))
    return rows

def guard_approval(app,policy):
    failed=[r['rule_id'] for r in checks(app,policy) if r['result']!='pass']
    if failed:raise ClientException('Journey requirements incomplete: '+', '.join(failed),status_code=409)

def update(s,a,j,actor,action):
    a.data={**a.data,'journey':j}
    audit(s,a.id,action,actor=actor,journey=j,recorded_at=now())
