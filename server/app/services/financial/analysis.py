from decimal import Decimal as D
from app.services.financial.calculators import monthly_summaries,full_months,emi,dscr,affordable_principal,money,amortize

def calculate(fields,txs,bank,app,policy,reconciliation):
    monthly=monthly_summaries(txs); months=None
    if bank and bank.get('period_start') and bank.get('period_end') and bank['expected_pages']==len(bank['pages_present']):months=full_months(bank['period_start'],bank['period_end'])
    bank_reconciled=any(r['comparison']=='Bank operating receipts / GST' and r['result']=='pass' for r in reconciliation)
    debts=[f for f in fields if f['name']=='existing_monthly_debt']
    declared=D(str(debts[0]['value'])) if len(debts)==1 else None
    observed=sum((D(str(row['debt'])) for row in monthly.values()),D(0))/months if months else None
    existing=max(declared,observed) if declared is not None and observed is not None else None
    unknown=any(row['unknown'] for row in monthly.values())
    net=sum((D(str(r['operating_credits']))-D(str(r['operating_debits'])) for r in monthly.values()),D(0))/months if months and bank_reconciled and not unknown else None
    payment=emi(app['requested_amount'],policy['annual_rate_percent'],app['tenure_months'])
    annual_cash=net*12 if net is not None else None
    annual_debt=(existing+payment)*12 if existing is not None else None
    ratio=dscr(annual_cash,annual_debt)
    eligible=affordable_principal(net,existing,policy['min_dscr'],policy['annual_rate_percent'],app['tenure_months'])
    refs=[f['evidence_id'] for f in fields]+[t['evidence_id'] for t in txs]
    return {'monthly':monthly,'complete_months':months,'bank_reconciled':bank_reconciled,'monthly_operating_cash':money(net) if net is not None else None,'existing_monthly_debt':money(existing) if existing is not None else None,'proposed_emi':money(payment),'annual_operating_cash':money(annual_cash) if annual_cash is not None else None,'annual_debt_service':money(annual_debt) if annual_debt is not None else None,'dscr':float(ratio) if ratio is not None else None,'eligible_principal':money(min(eligible,D(str(policy['max_principal'])))) if eligible is not None else None,'annual_rate_percent':policy['annual_rate_percent'],'amortization':amortize(app['requested_amount'],policy['annual_rate_percent'],app['tenure_months']),'evidence_ids':refs,'units':{'money':'INR','dscr':'ratio','rate':'nominal annual percent, monthly reducing balance'},'formulas':{'monthly_operating_cash':'(classified operating credits - classified operating debits) / complete covered months, only after GST reconciliation','existing_monthly_debt':'max(declared debt, observed debt payments / covered months); declaration required','dscr':'annual operating cash / (12 * (existing monthly debt + proposed EMI))','emi':'P*r*(1+r)^n / ((1+r)^n-1), r=annual percent/1200; zero rate P/n','eligible_principal':'max(0, monthly cash / minimum DSCR - existing debt) / EMI(1 INR), capped by demo product limit'},'inputs':{'requested_amount':app['requested_amount'],'tenure_months':app['tenure_months'],'policy_version':policy['version']},'assumptions':['Synthetic documents only.','Operating classification is a supplied assertion; GST matching is a consistency check, not independent verification.','Cash-basis receipts and GST turnover cover identical periods; accounting differences require clarification.','No seasonal extrapolation adjustment; short-period cash is annualized and requires human review.','Unknown categories block operating cash; missing debt is not zero.','Duplicate bank references are counted once and require investigation.','Complete periods rely on declared bank page inventory; not bank-authenticated.']}
