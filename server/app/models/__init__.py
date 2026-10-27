from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, JSON, ForeignKey, UniqueConstraint, event, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.config import settings

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
class Row:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String, default=now)
class User(Row, Base):
    __tablename__='users'
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
class Application(Row, Base):
    __tablename__='applications'
    data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default='draft', index=True)
    revision: Mapped[int] = mapped_column(default=0)
    analyzed_revision: Mapped[int] = mapped_column(default=-1)
class CaseRow(Row):
    case_id: Mapped[str] = mapped_column(ForeignKey('applications.id'), index=True)
class Document(CaseRow, Base):
    __tablename__='documents'
    name: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='uploaded')
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__=(UniqueConstraint('case_id','sha256'),)
class ExtractedField(CaseRow, Base):
    __tablename__='extracted_fields'
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'))
    data: Mapped[dict] = mapped_column(JSON)
class Transaction(CaseRow, Base):
    __tablename__='transactions'
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'))
    data: Mapped[dict] = mapped_column(JSON)
class AgentRun(CaseRow, Base):
    __tablename__='agent_runs'
    revision: Mapped[int] = mapped_column()
    node: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__=(UniqueConstraint('case_id','revision','node'),)
class ReconciliationFinding(CaseRow, Base):
    __tablename__='reconciliation_findings'
    revision: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)
class FinancialMetric(CaseRow, Base):
    __tablename__='financial_metrics'
    revision: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)
class RiskFlag(CaseRow, Base):
    __tablename__='risk_flags'
    revision: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)
class PolicyRule(Row, Base):
    __tablename__='policy_rules'
    version: Mapped[str] = mapped_column(String, unique=True)
    data: Mapped[dict] = mapped_column(JSON)
class PolicyEvaluation(CaseRow, Base):
    __tablename__='policy_evaluations'
    revision: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)
class EvidenceRequest(CaseRow, Base):
    __tablename__='evidence_requests'
    revision: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String, default='open')
    data: Mapped[dict] = mapped_column(JSON)
class CamVersion(CaseRow, Base):
    __tablename__='cam_versions'
    revision: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)
    __table_args__=(UniqueConstraint('case_id','revision'),)
class ReviewDecision(CaseRow, Base):
    __tablename__='review_decisions'
    reviewer_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    revision: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)
class AuditEvent(CaseRow, Base):
    __tablename__='audit_events'
    data: Mapped[dict] = mapped_column(JSON)
class MockLedgerEntry(CaseRow, Base):
    __tablename__='mock_ledger_entries'
    decision_id: Mapped[str] = mapped_column(ForeignKey('review_decisions.id'), unique=True)
    data: Mapped[dict] = mapped_column(JSON)
    __table_args__=(UniqueConstraint('case_id'),)

class SyntheticProfile(Row, Base):
    __tablename__='synthetic_profiles'
    mobile: Mapped[str] = mapped_column(String, unique=True)
    data: Mapped[dict] = mapped_column(JSON)
class DemoChallenge(Row, Base):
    __tablename__='demo_otp_challenges'
    mobile: Mapped[str] = mapped_column(String, index=True)
    data: Mapped[dict] = mapped_column(JSON)
class BorrowerSession(Row, Base):
    __tablename__='borrower_sessions'
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey('synthetic_profiles.id'))
    expires_at: Mapped[float] = mapped_column()

class VoiceSession(CaseRow, Base):
    __tablename__='voice_sessions'
    actor: Mapped[str] = mapped_column(String)
    ticket_hash: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='pending')
    expires_at: Mapped[float] = mapped_column()
    revision: Mapped[int] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)

engine=create_engine(settings.database_url, connect_args={'check_same_thread':False} if settings.database_url.startswith('sqlite') else {}, pool_pre_ping=True)
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _): connection.execute('PRAGMA foreign_keys=ON')
Session=sessionmaker(engine, expire_on_commit=False)

def migrate():
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        if engine.dialect.name=='sqlite':
            for table in ['audit_events','review_decisions']:
                for operation in ['UPDATE','DELETE']:
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only table'); END"))
        else:
            c.execute(text("CREATE OR REPLACE FUNCTION reject_history_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'append-only table'; END; $$"))
            for table in ['audit_events','review_decisions']:
                c.execute(text(f'DROP TRIGGER IF EXISTS immutable_history ON {table}'))
                c.execute(text(f'CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_history_change()'))
    from app.services.policy.engine import DEFAULT_POLICY
    with Session.begin() as s:
        if not s.get(User,'reviewer-local'): s.add(User(id='reviewer-local',name='Local demo reviewer',role='reviewer'))
        rule=s.query(PolicyRule).filter_by(version=DEFAULT_POLICY['version']).first()
        if rule and rule.data!=DEFAULT_POLICY:raise RuntimeError('Policy version already exists with different values; increment version')
        if not rule:s.add(PolicyRule(version=DEFAULT_POLICY['version'],data=DEFAULT_POLICY))
        from app.services.integrations.synthetic import seed_profiles
        seed_profiles(s,100)

def audit(s, case_id, action, **data):
    s.add(AuditEvent(case_id=case_id,data={'action':action,**data}))

