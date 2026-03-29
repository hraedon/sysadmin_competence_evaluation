from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, text, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy import create_engine
import datetime
import uuid
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./lab_state.db")

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")


# ---------------------------------------------------------------------------
# Custom type: UTC-aware DateTime (needed for SQLite; PostgreSQL handles TZ natively)
# ---------------------------------------------------------------------------

class UTCDateTime(TypeDecorator):
    """Enforce UTC-awareness for DateTime objects."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value.astimezone(datetime.timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value
        return value


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class LabEnvironment(Base):
    __tablename__ = "environments"

    id = Column(String, primary_key=True, index=True)
    vms = Column(JSON)  # List of VM names: ["Env01-DC01", "Env01-SRV01"]
    guac_connection_id = Column(String) # Static ID for fallback (legacy)
    guac_target_vm = Column(String, nullable=True) # VM to connect to
    guac_protocol = Column(String, nullable=True)  # rdp or ssh
    capabilities = Column(JSON)  # ["windows-domain", "ad-ds"]
    status = Column(String, default="available")  # available, provisioning, busy, teardown, faulted
    provision_step = Column(String, nullable=True)  # reverting, starting, waiting_ip, testing_connectivity, creating_guac, running_scripts
    provision_step_updated_at = Column(UTCDateTime, nullable=True)
    last_error = Column(String, nullable=True)
    updated_at = Column(UTCDateTime, default=lambda: datetime.datetime.now(datetime.UTC), onupdate=lambda: datetime.datetime.now(datetime.UTC))
    # Reconciler fields: track when faults occurred and how many auto-recovery attempts have run
    faulted_at = Column(UTCDateTime, nullable=True)       # timestamp of most recent fault entry
    fault_retry_count = Column(Integer, default=0)     # number of auto-recovery attempts since last manual reset


class LabSession(Base):
    __tablename__ = "sessions"

    session_token = Column(String, primary_key=True, index=True)
    environment_id = Column(String, ForeignKey("environments.id"))
    user_id = Column(String)
    scenario_id = Column(String)
    guac_connection_id = Column(String, nullable=True)
    guac_session_username = Column(String, nullable=True)  # SEC-07: per-session Guac user
    guac_session_password = Column(String, nullable=True)  # SEC-07: per-session Guac user password
    suspect = Column(Boolean, default=False)  # ARCH-02: marked on restart, reaper handles teardown
    verification_results = Column(JSON, nullable=True)  # ARCH-17: stored by /lab/verify for AI context
    created_at = Column(UTCDateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    expires_at = Column(UTCDateTime)
    max_expires_at = Column(UTCDateTime)  # Hard cap (e.g., 4h)


class LabHeartbeat(Base):
    __tablename__ = "heartbeats"

    job_name = Column(String, primary_key=True)
    last_run_at = Column(UTCDateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    last_status = Column(String)  # success, error
    last_error = Column(String, nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # null for OAuth users
    role = Column(String, default="learner")  # learner | admin
    auth_provider = Column(String, default="local")  # local | oauth2
    created_at = Column(UTCDateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    last_login_at = Column(UTCDateTime, nullable=True)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, index=True)
    data = Column(JSON)  # Full profile: { updated, domains: { [domain]: { domain_name, results: [...] } } }
    updated_at = Column(UTCDateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    scenario_id = Column(String, index=True)
    response_text = Column(String)
    model_used = Column(String)
    raw_result = Column(JSON)
    parsed_result = Column(JSON)
    level = Column(Integer, nullable=True)
    confidence = Column(String, nullable=True)
    verification_results = Column(JSON, nullable=True)  # ARCH-17: lab verification data
    created_at = Column(UTCDateTime, default=lambda: datetime.datetime.now(datetime.UTC))


# ---------------------------------------------------------------------------
# Engine and session factory
# ---------------------------------------------------------------------------

def _create_engine():
    if _is_sqlite:
        return create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
    else:
        return create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# SQLite-specific pragmas (only when using SQLite)
# ---------------------------------------------------------------------------

if _is_sqlite:
    import sqlite3
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_wal(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_db():
    """Initialize the database.

    For SQLite (dev/tests): uses create_all for speed.
    For PostgreSQL (production): runs Alembic migrations.
    """
    if _is_sqlite:
        Base.metadata.create_all(bind=engine)
    else:
        from alembic.config import Config
        from alembic import command
        import os

        alembic_ini = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
        command.upgrade(alembic_cfg, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
