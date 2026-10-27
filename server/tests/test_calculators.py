from decimal import Decimal as D
import pytest
from app.services.financial.calculators import *
def test_emi_and_amortization():
    assert money(emi(1000000,14,36))==34177.63
    rows=amortize(1000000,14,36)
    assert rows[-1]['balance']==0
    assert abs(sum(r['principal'] for r in rows)-1000000)<.1
    assert emi(1200,0,12)==100
    with pytest.raises(ValueError):emi(10,2,0)
def test_unknown_and_zero_dscr():
    assert dscr(None,10) is None
    assert dscr(10,0) is None
    assert dscr(D(100),D(50))==2
    assert affordable_principal(None,D(0),1.25,14,36) is None
def test_periods_and_tolerance():
    assert full_months('2025-04-01','2026-03-31')==12
    assert full_months('2025-04-02','2026-03-31') is None
    assert within_tolerance(D(100),D(105),.05,0)
    assert within_tolerance(None,1,.05,1) is None
