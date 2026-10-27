"""Seed persisted synthetic cases through the same API used by the frontend."""
import argparse,json,os
from pathlib import Path
import httpx
p=argparse.ArgumentParser();p.add_argument('--url',default='http://localhost:8000');p.add_argument('--scenario',default='01_consistent');args=p.parse_args()
folder=Path(__file__).resolve().parents[1]/'fixtures'/'synthetic_cases'
files=sorted(folder.glob('*.json')) if args.scenario=='all' else [folder/(args.scenario+'.json')]
with httpx.Client(base_url=args.url,headers={'Authorization':'Bearer '+os.getenv('ANALYST_TOKEN','local-analyst-change-me')},timeout=180,trust_env=False) as c:
 for file in files:
  data=json.loads(file.read_text());app={**data['application'],'business':data['application']['business']+' / '+file.stem};r=c.post('/api/applications',json=app);r.raise_for_status();id=r.json()['id']
  for d in data['documents']:
   r=c.post(f'/api/applications/{id}/documents',params={'kind':d['kind']},files={'data':(d['kind']+'.json',json.dumps(d).encode(),'application/json')});r.raise_for_status()
  r=c.post(f'/api/applications/{id}/runs',json={});r.raise_for_status();print(file.stem,id,r.json())
