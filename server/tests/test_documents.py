import json
from pathlib import Path
import fitz
import pytest
from app.services.documents.parser import parse
from app.agents.specialists import explain

def test_pdf_template_and_rejection(tmp_path):
    p=tmp_path/'kyc.pdf'
    with fitz.open() as d:
        page=d.new_page();page.insert_text((36,36),'SYNTHETIC: true\nDOCUMENT_KIND: kyc\nEXPECTED_PAGES: 1\nFIELD|legal_name|Sample Person\nFIELD|tax_id|SYN-TAX-001');d.save(p)
    result=parse(p);assert result['fields'][0]['value']=='Sample Person';assert result['fields'][0]['page']==1
    with fitz.open() as d:
        page=d.new_page();page.insert_text((36,36),'Unrecognized bank format. No data should be guessed from this document.');d.save(tmp_path/'unknown.pdf')
    with pytest.raises(ValueError):parse(tmp_path/'unknown.pdf')

def test_llm_unavailable_retains_deterministic_mode(monkeypatch):
    import app.agents.specialists as mod
    from types import SimpleNamespace
    monkeypatch.setattr(mod,'settings',SimpleNamespace(llm_mode='ollama',ollama_model='',ollama_host='http://127.0.0.1:1'))
    result=explain({'evidence_ids':[]});assert result['status']=='unavailable'
