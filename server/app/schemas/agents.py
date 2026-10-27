from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from app.schemas import AgentOutput
class Output(BaseModel):
    model_config=ConfigDict(extra='allow')
class DocumentResult(Output):
    gaps:list[str]
    errors:list[dict]
    fields:list[dict]
    transactions:list[dict]
    bank:dict|None
    agent:AgentOutput
class CashFlowResult(Output):
    monthly:dict[str,dict[str,float]]
    complete_months:int|None
    bank_reconciled:bool
    monthly_operating_cash:float|None
    existing_monthly_debt:float|None
    proposed_emi:float
    annual_operating_cash:float|None
    annual_debt_service:float|None
    dscr:float|None
    eligible_principal:float|None
    formulas:dict[str,str]
    inputs:dict
    units:dict[str,str]
    assumptions:list[str]
    evidence_ids:list[str]
class FraudFinding(Output):
    kind:str
    severity:Literal['review']
    classification:Literal['confirmed_inconsistency','unverified_suspicion','limitation','observed_fact']
    message:str
    evidence_ids:list[str]
class RiskResult(Output):
    outcome:Literal['manual_review','rules_only']
    no_predictive_score:Literal[True]
    evidence_ids:list[str]
    findings:list[dict]
    leverage:str
class PolicyCheck(Output):
    rule_id:str
    rule_version:str
    inputs:dict
    result:Literal['pass','fail','exception','insufficient_evidence']
    reason:str
    evidence_ids:list[str]
class Proposal(Output):
    status:Literal['proposal_requires_review','blocked_pending_evidence_or_policy']
    requested_principal:str|float
    proposed_principal:float|None
    capacity_limit:float|None
    monthly_installment:float
    tenure_months:int
    nominal_annual_rate_percent:float
    rationale:str
    evidence_ids:list[str]
class CamResult(Output):
    title:str
    revision:int
    applicant:dict
    policy_version:str
    outcome:Literal['proposed_for_review','manual_review']
    financial_analysis:CashFlowResult
    investigation_flags:list[FraudFinding]
    policy_checks:list[PolicyCheck]
    proposal:Proposal
    evidence_gaps:list[str]
    evidence_ids:list[str]
    limitations:list[str]
    model_explanation:dict
class ReconciliationResult(Output):
    comparison:str
    result:Literal['pass','conflict','insufficient_evidence']
    reason:str
    evidence_ids:list[str]
def validate_node(node,result):
    scalar={'documents':DocumentResult,'cashflow':CashFlowResult,'risk':RiskResult,'structure':Proposal,'cam':CamResult}
    lists={'fraud':FraudFinding,'policy':PolicyCheck,'reconciliation':ReconciliationResult}
    if node in scalar:return scalar[node].model_validate(result).model_dump(mode='json')
    return [lists[node].model_validate(x).model_dump(mode='json') for x in result]
