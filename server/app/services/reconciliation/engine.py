from decimal import Decimal
from app.services.financial.calculators import within_tolerance, unique_transactions

def reconcile(fields,txs,bank,policy):
    output=[]
    values={name:[f for f in fields if f['name']==name] for name in ['gst_turnover','itr_turnover','financial_turnover']}
    gst=values['gst_turnover']; itr=values['itr_turnover']; fin=values['financial_turnover']
    for name,group in values.items():
        if len(group)>1 and len({(f['value'],f.get('period_start'),f.get('period_end')) for f in group})>1:
            output.append({'comparison':name,'result':'conflict','evidence_ids':[f['evidence_id'] for f in group],'reason':'Multiple inconsistent declarations require explicit correction.'})
    pairs=[('GST / ITR',gst,itr),('GST / financial',gst,fin)]
    for title,left,right in pairs:
        refs=[f['evidence_id'] for f in left+right]
        result='insufficient_evidence'; inputs={}
        if len(left)==len(right)==1:
            a,b=left[0],right[0];inputs={'left':a['value'],'right':b['value'],'period_start':a.get('period_start'),'period_end':a.get('period_end')}
            if a.get('period_start') and a.get('period_end') and (a['period_start'],a['period_end'])==(b.get('period_start'),b.get('period_end')):
                result='pass' if within_tolerance(Decimal(str(a['value'])),Decimal(str(b['value'])),policy['reconciliation_relative'],policy['reconciliation_absolute_inr']) else 'conflict'
        output.append({'comparison':title,'result':result,'inputs':inputs,'evidence_ids':refs,'reason':'Matching reporting periods required; compare normalized INR amounts.'})
    result='insufficient_evidence'; inputs={};refs=[]
    if bank and len(gst)==1:
        a=gst[0]; refs=[a['evidence_id']]+[t['evidence_id'] for t in txs if t['category']=='operating' and t['direction']=='credit']
        if a.get('period_start')==bank.get('period_start') and a.get('period_end')==bank.get('period_end'):
            # Document labels are claims, not independently verified bank revenue.
            receipts=sum((Decimal(str(t['amount'])) for t in unique_transactions(txs) if t['category']=='operating' and t['direction']=='credit'),Decimal(0))
            inputs={'classified_operating_credits':float(receipts),'gst_turnover':a['value'],'excludes':'transfers, loans, refunds, unknown'}
            result='pass' if within_tolerance(receipts,Decimal(str(a['value'])),policy['reconciliation_relative'],policy['reconciliation_absolute_inr']) else 'conflict'
    output.append({'comparison':'Bank operating receipts / GST','result':result,'inputs':inputs,'evidence_ids':refs,'reason':'Demo uses cash-basis comparison; timing/GST treatment differences require reviewer evidence.'})
    return output
