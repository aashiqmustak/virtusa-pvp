"""Idempotent initial schema migration, including append-only audit triggers.
Run: python migrations/001_initial.py from server. Future schema changes need
new numbered migrations; create_all does not upgrade existing columns.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.models import migrate
migrate()
