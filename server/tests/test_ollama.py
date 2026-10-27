from types import SimpleNamespace
from app.agents.specialists import explain

def test_real_adapter_connection_failure(monkeypatch):
    import app.agents.specialists as mod
    monkeypatch.setattr(mod,'settings',SimpleNamespace(llm_mode='ollama',ollama_model='not-installed',ollama_host='http://127.0.0.1:1',llm_timeout=.3,llm_retries=0))
    result=explain({'evidence_ids':[],'policy':[]})
    assert result['status']=='unavailable'
    assert result['error_type']!='TypeError' # Adapter configuration itself must be valid.
