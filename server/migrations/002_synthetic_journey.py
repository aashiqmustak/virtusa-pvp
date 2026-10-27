"""Additive v0.2 migration: create profile, OTP and borrower session tables.
Startup migrate() also runs this metadata create_all path. No existing columns or
case records are deleted or changed. Run against a backed-up demo database.
"""
from app.models import migrate
if __name__=='__main__':migrate()
