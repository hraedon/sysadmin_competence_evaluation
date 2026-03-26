from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime
import uuid

SQLALCHEMY_DATABASE_URL = "sqlite:///./lab_state.db"
Base = declarative_base()

class LabEnvironment(Base):
    __tablename__ = "environments"

    id = Column(String, primary_key=True, index=True)
    vms = Column(JSON)  # List of VM names: ["Env01-DC01", "Env01-SRV01"]
    guac_connection_id = Column(String)
    capabilities = Column(JSON)  # ["windows-domain", "ad-ds"]
    status = Column(String, default="available")  # available, provisioning, busy, teardown, faulted
    last_error = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class LabSession(Base):
    __tablename__ = "sessions"

    session_token = Column(String, primary_key=True, index=True)
    environment_id = Column(String, ForeignKey("environments.id"))
    user_id = Column(String)
    scenario_id = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)
    max_expires_at = Column(DateTime)  # Hard cap (e.g., 4h)

# Initialize engine and session
from sqlalchemy import create_engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
