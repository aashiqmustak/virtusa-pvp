import os
from dataclasses import dataclass
from pathlib import Path

def _normalize_db_url(url: str) -> str:
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+psycopg://', 1)
    if url.startswith('postgresql://') and not url.startswith('postgresql+'):
        return url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url

@dataclass(frozen=True)
class Settings:
    database_url: str = _normalize_db_url(os.getenv('DATABASE_URL', 'sqlite:///./demo.db'))
    storage: Path = Path(os.getenv('PRIVATE_STORAGE', './private_uploads'))
    analyst_token: str = os.getenv('ANALYST_TOKEN', 'local-analyst-change-me')
    reviewer_token: str = os.getenv('REVIEWER_TOKEN', 'local-reviewer-change-me')
    cors_origins: str = os.getenv('CORS_ALLOWED_ORIGINS', '*')
    llm_mode: str = os.getenv('LLM_MODE', 'mock')
    ollama_host: str = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    ollama_model: str = os.getenv('OLLAMA_MODEL', '')
    llm_timeout: float = float(os.getenv('LLM_TIMEOUT', '45'))
    llm_retries: int = int(os.getenv('LLM_RETRIES', '1'))
    voice_mode: str = os.getenv('VOICE_MODE','mock')
    sarvam_api_key: str = os.getenv('SARVAM_API_KEY','')
    sarvam_stt_model: str = os.getenv('SARVAM_STT_MODEL','saaras:v3-realtime')
    sarvam_tts_model: str = os.getenv('SARVAM_TTS_MODEL','bulbul:v3')
    sarvam_voice: str = os.getenv('SARVAM_VOICE','shubh')
    voice_origins: str = os.getenv('VOICE_ALLOWED_ORIGINS','*')
    max_upload: int = 10 * 1024 * 1024
    max_pages: int = 50
settings = Settings()
