from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid', str_strip_whitespace=True)
class ApplicationInput(Strict):
    applicant: str = Field(min_length=2,max_length=120)
    business: str = Field(min_length=2,max_length=120)
    purpose: str = Field(min_length=3,max_length=500)
    requested_amount: Decimal = Field(gt=0,le=100000000)
    tenure_months: int = Field(ge=1,le=120)
    synthetic: Literal[True]
class ReviewInput(Strict):
    decision: Literal['approve','reject','request_evidence']
    revision: int = Field(ge=0)
    comments: str = Field(min_length=3,max_length=2000)
class EvidenceInput(Strict):
    message: str = Field(min_length=3,max_length=2000)
class FieldValue(Strict):
    name: Literal['gst_turnover','itr_turnover','financial_turnover','existing_monthly_debt','legal_name','tax_id']
    value: str | Decimal
    page: int = Field(ge=1)
    source_text: str = Field(min_length=1,max_length=2000)
    period_start: date | None = None
    period_end: date | None = None
class Tx(Strict):
    transaction_id: str = Field(min_length=1,max_length=100)
    date: date
    amount: Decimal = Field(gt=0,le=100000000000)
    direction: Literal['credit','debit']
    category: Literal['operating','transfer','loan','refund','debt','unknown']
    from_account: str = Field(min_length=1,max_length=100)
    to_account: str = Field(min_length=1,max_length=100)
    page: int = Field(ge=1)
    balance: Decimal | None = None
    source_text: str = Field(min_length=1,max_length=2000)
class DocumentInput(Strict):
    synthetic: Literal[True]
    kind: Literal['bank','gst','itr','financial','kyc','bureau']
    period_start: date | None = None
    period_end: date | None = None
    expected_pages: int = Field(ge=1,le=50)
    pages_present: list[int] = Field(min_length=1,max_length=50)
    fields: list[FieldValue] = Field(default_factory=list,max_length=200)
    transactions: list[Tx] = Field(default_factory=list,max_length=5000)
    @model_validator(mode='after')
    def periods(self):
        if self.period_start and self.period_end and self.period_start>self.period_end: raise ValueError('Invalid reporting period')
        if len(set(self.pages_present))!=len(self.pages_present) or any(x<1 or x>self.expected_pages for x in self.pages_present): raise ValueError('Invalid page inventory')
        for item in [*self.fields,*self.transactions]:
            if item.page not in self.pages_present: raise ValueError('Evidence points to absent page')
        for f in self.fields:
            if f.period_start and f.period_end and f.period_start>f.period_end: raise ValueError('Invalid field period')
            if f.name not in ['legal_name','tax_id']:
                v=Decimal(str(f.value))
                if not v.is_finite() or v<0: raise ValueError('Financial value must be finite and nonnegative')
        if self.transactions:
            if not self.period_start or not self.period_end: raise ValueError('Bank transactions need coverage dates')
            if any(t.date<self.period_start or t.date>self.period_end for t in self.transactions): raise ValueError('Transaction outside period')
        return self
class AgentOutput(Strict):
    agent: str
    version: str = '1.0'
    outcome: Literal['complete','manual_review','insufficient_data']
    evidence_ids: list[str] = []
    findings: list[dict] = []
class Explanation(Strict):
    explanation: str = Field(max_length=1600)
    evidence_ids: list[str] = Field(max_length=30)
