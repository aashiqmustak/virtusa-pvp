from decimal import Decimal, ROUND_HALF_UP
from datetime import date
D=Decimal
def money(v): return float(D(str(v)).quantize(D('.01'),rounding=ROUND_HALF_UP))
def emi(principal, annual_rate, months):
    p,r=D(str(principal)),D(str(annual_rate))/1200
    if p<0 or r<0 or months<=0: raise ValueError('Invalid loan terms')
    return p/months if r==0 else p*r*(1+r)**months/((1+r)**months-1)
def amortize(principal, annual_rate, months):
    balance=D(str(principal)); payment=emi(balance,annual_rate,months); rows=[]
    for month in range(1,months+1):
        interest=balance*D(str(annual_rate))/1200
        paid=min(balance,payment-interest); balance-=paid
        rows.append({'month':month,'principal':money(paid),'interest':money(interest),'balance':money(balance)})
    return rows

def dscr(annual_cash, annual_debt):
    if annual_cash is None or annual_debt is None or annual_debt<=0: return None
    return annual_cash/annual_debt

def affordable_principal(monthly_cash, existing_debt, min_dscr, annual_rate, months):
    if monthly_cash is None or existing_debt is None: return None
    payment=max(D(0),monthly_cash/D(str(min_dscr))-existing_debt)
    return payment/emi(1,annual_rate,months)

def within_tolerance(a,b,relative,absolute):
    if a is None or b is None: return None
    return abs(a-b)<=max(D(str(absolute)),max(abs(a),abs(b))*D(str(relative)))

def duplicate_groups(txs):
    seen={}; groups=[]
    for t in txs:
        # Stable account + bank reference; a shared amount/date alone is not proof of duplication.
        key=(t['from_account'],t['to_account'],t['transaction_id'])
        if key in seen: groups.append([seen[key]['evidence_id'],t['evidence_id']])
        else: seen[key]=t
    return groups

def unique_transactions(txs):
    seen=set(); output=[]
    for t in txs:
        key=(t['from_account'],t['to_account'],t['transaction_id'])
        if key not in seen: output.append(t); seen.add(key)
    return output

def monthly_summaries(txs):
    result={}
    for t in unique_transactions(txs):
        m=t['date'][:7]; row=result.setdefault(m,{'credits':D(0),'debits':D(0),'operating_credits':D(0),'operating_debits':D(0),'debt':D(0),'unknown':D(0)})
        value=D(str(t['amount'])); row['credits' if t['direction']=='credit' else 'debits']+=value
        if t['category']=='operating': row['operating_credits' if t['direction']=='credit' else 'operating_debits']+=value
        if t['category']=='debt' and t['direction']=='debit': row['debt']+=value
        if t['category']=='unknown': row['unknown']+=value
    return {m:{k:money(v) for k,v in row.items()} for m,row in sorted(result.items())}

def full_months(start,end):
    import calendar
    a=date.fromisoformat(start); b=date.fromisoformat(end)
    if a.day!=1 or b.day!=calendar.monthrange(b.year,b.month)[1]: return None
    return (b.year-a.year)*12+b.month-a.month+1
