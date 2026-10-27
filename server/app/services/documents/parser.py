import json, re, subprocess, tempfile
from pathlib import Path
import fitz
from app.schemas import DocumentInput
from app.config import settings

def parse(path):
    raw=Path(path).read_bytes()
    if not raw.startswith(b'%PDF-'):
        obj=DocumentInput.model_validate_json(raw)
        return obj.model_dump(mode='json')
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        if pdf.needs_pass or len(pdf)>settings.max_pages or len(pdf)==0: raise ValueError('Encrypted, empty or excessive page PDF')
        pages=[]
        for page in pdf:
            if page.rect.width*page.rect.height*(150/72)**2>15000000:raise ValueError('PDF page raster exceeds 15 megapixel limit')
            txt=page.get_text()
            if len(txt)>200000:raise ValueError('PDF page text exceeds extraction boundary')
            if len(txt.strip())<20:
                # OCR in a bounded process. One page at a time, 150 DPI, no shell execution.
                with tempfile.TemporaryDirectory() as folder:
                    p=Path(folder)/'page.png'; page.get_pixmap(matrix=fitz.Matrix(150/72,150/72)).save(p)
                    try:txt=subprocess.run(['tesseract',str(p),'stdout','--psm','6'],capture_output=True,text=True,timeout=20,check=True).stdout
                    except (OSError,subprocess.SubprocessError):raise ValueError(f'Page {page.number+1} unreadable; OCR failed')
            pages.append(txt)
        # Deliberately conservative template extraction. No guessed bank table layouts.
        combined='\n'.join(pages)
        kind_match=re.search(r'^DOCUMENT_KIND:\s*(bank|gst|itr|financial|kyc|bureau)\s*$',combined,re.M)
        if not kind_match or 'SYNTHETIC: true' not in combined:raise ValueError('Use the documented synthetic PDF template or JSON schema; general PDFs require manual mapping')
        def label(name):
            m=re.search(r'^'+name+r':\s*(.+)$',combined,re.M)
            return m.group(1).strip() if m else None
        obj={'synthetic':True,'kind':kind_match.group(1),'expected_pages':int(label('EXPECTED_PAGES') or len(pdf)), 'pages_present':list(range(1,len(pdf)+1)),'period_start':label('PERIOD_START'),'period_end':label('PERIOD_END'),'fields':[],'transactions':[]}
        for i,txt in enumerate(pages,1):
            for line in txt.splitlines():
                if line.startswith('FIELD|'):
                    _,name,value=line.split('|',2)
                    obj['fields'].append({'name':name,'value':value,'page':i,'source_text':line,'period_start':obj['period_start'],'period_end':obj['period_end']})
                elif line.startswith('TX|'):
                    values=line.split('|')
                    if len(values)!=10:raise ValueError('Malformed TX line')
                    _,ref,day,amount,direction,category,source,target,balance,_=values
                    obj['transactions'].append({'transaction_id':ref,'date':day,'amount':amount,'direction':direction,'category':category,'from_account':source,'to_account':target,'balance':balance or None,'page':i,'source_text':line})
        return DocumentInput.model_validate(obj).model_dump(mode='json')


def parse_isolated(path):
    import sys,os
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[3])}
    result=subprocess.run([sys.executable,'-m','app.services.documents.worker',str(Path(path).resolve())],capture_output=True,text=True,timeout=float(os.getenv('DOCUMENT_TIMEOUT','90')),env=env)
    if result.returncode:raise ValueError(result.stderr[-500:] or 'Document worker failed')
    return DocumentInput.model_validate_json(result.stdout).model_dump(mode='json')
