DEFAULT_POLICY={'version':'demo-2026.1','min_months':6,'min_dscr':1.25,'max_principal':5000000,'max_tenure':60,'annual_rate_percent':14,'reconciliation_relative':0.05,'reconciliation_absolute_inr':1000}

def evaluate(metrics, reconciliation, flags, gaps, requested, tenure, policy):
    def rule(id, inputs, outcome, reason):
        return {'rule_id':id,'rule_version':policy['version'],'inputs':inputs,'result':outcome,'reason':reason,'evidence_ids':metrics.get('evidence_ids',[])}
    checks=[]
    checks.append(rule('EVIDENCE',{'gaps':gaps},'insufficient_evidence' if gaps else 'pass','Required readable KYC, bank, GST, ITR and financial evidence.'))
    months=metrics.get('complete_months')
    checks.append(rule('COVERAGE',{'months':months,'minimum':policy['min_months']},'insufficient_evidence' if months is None else ('pass' if months>=policy['min_months'] else 'fail'),'Complete bank months only.'))
    ratio=metrics.get('dscr')
    checks.append(rule('DSCR',{'value':ratio,'minimum':policy['min_dscr']},'insufficient_evidence' if ratio is None else ('pass' if ratio>=policy['min_dscr'] else 'fail'),'Annual operating cash / annual existing and proposed debt service.'))
    checks.append(rule('LIMIT',{'amount':requested,'maximum':policy['max_principal'],'tenure':tenure,'max_tenure':policy['max_tenure']},'pass' if requested<=policy['max_principal'] and tenure<=policy['max_tenure'] else 'fail','Configured demo product limits.'))
    checks.append(rule('RECONCILIATION',{'results':[r['result'] for r in reconciliation]},'exception' if any(r['result']=='conflict' for r in reconciliation) else ('insufficient_evidence' if any(r['result']=='insufficient_evidence' for r in reconciliation) else 'pass'),'Same-period turnover comparison using demo tolerance.'))
    checks.append(rule('INVESTIGATION',{'flag_count':len(flags)},'exception' if flags else 'pass','Investigation flags require evidence resolution before approval.'))
    return checks


from pydantic import BaseModel,Field,ConfigDict
class DemoPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version:str=Field(min_length=1,max_length=80)
    min_months:int=Field(ge=1,le=60)
    min_dscr:float=Field(gt=0,le=10)
    max_principal:float=Field(gt=0)
    max_tenure:int=Field(ge=1,le=120)
    annual_rate_percent:float=Field(ge=0,le=100)
    reconciliation_relative:float=Field(ge=0,le=1)
    reconciliation_absolute_inr:float=Field(ge=0)
import os,json
from pathlib import Path
if os.getenv('POLICY_FILE'):
    DEFAULT_POLICY=DemoPolicy.model_validate_json(Path(os.environ['POLICY_FILE']).read_text()).model_dump()
else:DEFAULT_POLICY=DemoPolicy.model_validate(DEFAULT_POLICY).model_dump()
