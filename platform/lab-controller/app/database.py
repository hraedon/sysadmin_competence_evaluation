from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import datetime
import uuid
import logging
from contextlib import contextmanager

import os

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./lab_state.db")
Base = declarative_base()

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
    provision_step_updated_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    # Reconciler fields: track when faults occurred and how many auto-recovery attempts have run
    faulted_at = Column(DateTime, nullable=True)       # timestamp of most recent fault entry
    fault_retry_count = Column(Integer, default=0)     # number of auto-recovery attempts since last manual reset

class LabSession(Base):
    __tablename__ = "sessions"

    session_token = Column(String, primary_key=True, index=True)
    environment_id = Column(String, ForeignKey("environments.id"))
    user_id = Column(String)
    scenario_id = Column(String)
    guac_connection_id = Column(String, nullable=True)
    suspect = Column(Boolean, default=False)  # ARCH-02: marked on restart, reaper handles teardown
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)
    max_expires_at = Column(DateTime)  # Hard cap (e.g., 4h)

# Initialize engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Enable WAL mode for concurrent read/write access.
# Without this, the long-running provisioning flow holds exclusive locks
# that block the session-status polling endpoint from reading.
from sqlalchemy import event
@event.listens_for(engine, "connect")
def _set_sqlite_wal(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    # Migration guard: create_all won't add columns to existing tables
    _migrate_add_columns()

def _migrate_add_columns():
    """Add columns that may be missing from an existing database."""
    migrations = [
        ("environments", "provision_step", "TEXT"),
        ("environments", "provision_step_updated_at", "TIMESTAMP"),
        ("sessions", "suspect", "BOOLEAN DEFAULT 0"),
        ("environments", "faulted_at", "TIMESTAMP"),
        ("environments", "fault_retry_count", "INTEGER DEFAULT 0"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
                logger.info(f"Migration: added {table}.{column}")
            except Exception:
                conn.rollback()  # column already exists

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
