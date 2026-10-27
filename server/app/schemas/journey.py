from typing import Literal
from decimal import Decimal
from pydantic import Field
from app.schemas import Strict
class OTPRequest(Strict):
    mobile:str=Field(pattern=r'^9[0-9]{9}$')
    purpose:Literal['login','kyc']='login'
class OTPVerify(Strict):
    challenge_id:str
    code:str=Field(pattern=r'^\d{6}$')
class BorrowerApplication(Strict):
    kyc_proof:str
    pan:str
    dob:str
    purpose:str=Field(min_length=3,max_length=500)
    requested_amount:Decimal=Field(gt=0,le=100000000)
    tenure_months:int=Field(ge=1,le=120)
    loan_type:Literal['term','working_capital','lap','construction']='term'
    consents:list[Literal['kyc','bank','tax','bureau','processing']]
class Verification(Strict):
    revision:int=Field(ge=0)
    channel:Literal['phone','video','voice']='phone'
    identity_verified:bool
    business_verified:bool
    purpose_verified:bool
    notes:str=Field(min_length=3,max_length=2000)
    market_assessment:str=Field(min_length=3,max_length=2000)
    surveyor:str=Field(max_length=120,default='')
    survey_reference:str=Field(max_length=160,default='')
    property_value:Decimal=Field(ge=0,le=1000000000,default=Decimal(0))
    margin_percent:Decimal=Field(ge=0,le=100,default=Decimal(0))
    title_clear:bool=False
class Terms(Strict):
    revision:int=Field(ge=0)
    amount:Decimal=Field(gt=0,le=100000000)
    tenure_months:int=Field(ge=1,le=120)
    annual_rate_percent:Decimal=Field(ge=0,le=100)
    reason:str=Field(min_length=3,max_length=2000)
class RateDecision(Strict):
    revision:int=Field(ge=0)
    approve:bool
    reason:str=Field(min_length=3,max_length=2000)

