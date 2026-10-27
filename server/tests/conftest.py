import os,tempfile
from pathlib import Path
import pytest
folder=tempfile.TemporaryDirectory();os.environ['DATABASE_URL']=os.getenv('TEST_DATABASE_URL','sqlite:///'+str(Path(folder.name)/'tests.db'));os.environ['PRIVATE_STORAGE']=str(Path(folder.name)/'uploads');os.environ['LLM_MODE']='mock'
os.environ['VOICE_MODE']='mock'
os.environ['ANALYST_TOKEN']='local-analyst-change-me'
os.environ['REVIEWER_TOKEN']='local-reviewer-change-me'
from litestar.testing import TestClient
from app.main import app
from app.models import *
@pytest.fixture
def client():
    with TestClient(app=app) as c:yield c
@pytest.fixture
def auth():return {'Authorization':'Bearer local-analyst-change-me'}
@pytest.fixture
def reviewer():return {'Authorization':'Bearer local-reviewer-change-me'}
@pytest.fixture
def fixture_data():
    import json
    return lambda name:json.loads((Path(__file__).resolve().parents[2]/'fixtures'/'synthetic_cases'/(name+'.json')).read_text())
@pytest.fixture
def load_case(client,auth,fixture_data):
    import json
    def load(name='01_consistent',analyze=True):
        data=fixture_data(name);r=client.post('/api/applications',json=data['application'],headers=auth);assert r.status_code==201,r.text
        id=r.json()['id']
        for doc in data['documents']:
            r=client.post(f'/api/applications/{id}/documents?kind='+doc['kind'],files={'data':(doc['kind']+'.json',json.dumps(doc).encode(),'application/json')},headers=auth);assert r.status_code==201,r.text
        if analyze:
            r=client.post(f'/api/applications/{id}/runs',json={},headers=auth);assert r.status_code==200,r.text
        return id,client.get('/api/applications/'+id,headers=auth).json()
    return load
