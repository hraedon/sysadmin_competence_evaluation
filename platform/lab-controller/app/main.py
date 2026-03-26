from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
import yaml
import os
import datetime
import uuid
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from .orchestrator import HyperVOrchestrator
from .guacamole import GuacamoleClient
from .database import init_db, get_db, LabEnvironment, LabSession
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Settings & Configuration
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    guacamole_url: str = "http://localhost:8080/guacamole"
    guacamole_username: str = ""
    guacamole_password: str = ""
    scenarios_dir: str = "../../scenarios"
    environments_config: str = "environments.yaml"
    session_timeout_minutes: int = 120
    max_session_hours: int = 4
    dry_run: bool = True

    class Config:
        env_file = ".env"

settings = Settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class LabAction(BaseModel):
    action: str
    target: Optional[str] = None
    file: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    name: Optional[str] = None

class LabConfig(BaseModel):
    provisioning: List[LabAction] = []
    cleanup: List[LabAction] = []

class ProvisionRequest(BaseModel):
    user_id: str
    capabilities: List[str] = []

class ProvisionResponse(BaseModel):
    status: str
    session_token: str
    environment_id: str
    guacamole_url: str
    expires_at: datetime.datetime
    instructions: str

class VerificationResult(BaseModel):
    finding_id: str
    status: str  # correct | workaround | incomplete
    detail: str

# ---------------------------------------------------------------------------
# Lifecycle & Initialization
# ---------------------------------------------------------------------------

app = FastAPI(title="Sysadmin Competency Lab Controller")
orchestrator = HyperVOrchestrator(dry_run=settings.dry_run)
guac_client = GuacamoleClient(
    settings.guacamole_url, 
    settings.guacamole_username, 
    settings.guacamole_password
)

@app.on_event("startup")
def startup_event():
    init_db()
    load_environments()
    
    # Start the reaper
    scheduler = BackgroundScheduler()
    scheduler.add_job(reap_expired_sessions, 'interval', minutes=1)
    scheduler.start()
    app.state.scheduler = scheduler

def load_environments():
    """Seed the database with environments from config if not already present."""
    if not os.path.exists(settings.environments_config):
        logger.warning(f"Environments config {settings.environments_config} not found.")
        return

    with open(settings.environments_config, 'r') as f:
        config = yaml.safe_load(f)
    
    db = next(get_db())
    for env_data in config.get('environments', []):
        existing = db.query(LabEnvironment).filter(LabEnvironment.id == env_data['id']).first()
        if not existing:
            env = LabEnvironment(
                id=env_data['id'],
                vms=env_data['vms'],
                guac_connection_id=env_data['guac_connection_id'],
                capabilities=env_data['capabilities'],
                status="available"
            )
            db.add(env)
    db.commit()
    db.close()

# ---------------------------------------------------------------------------
# Reaper & Teardown
# ---------------------------------------------------------------------------

def reap_expired_sessions():
    """Background task to clean up expired lab environments."""
    db = next(get_db())
    now = datetime.datetime.utcnow()
    
    expired = db.query(LabSession).filter(LabSession.expires_at < now).all()
    for session in expired:
        logger.info(f"Reaping expired session {session.session_token} for env {session.environment_id}")
        teardown_environment(session.environment_id, session.session_token)
    
    db.close()

def teardown_environment(env_id: str, session_token: str):
    """Reverts VMs and marks environment as available."""
    db = next(get_db())
    env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
    if not env:
        db.close()
        return

    env.status = "teardown"
    db.commit()

    try:
        # Assuming all VMs in the pool use the same 'Baseline' checkpoint for now
        # In the future, this could be scenario-specific if we don't revert to absolute zero
        checkpoint = "Baseline" 
        
        success = True
        for vm in env.vms:
            logger.info(f"Teardown: Reverting {vm}")
            res = orchestrator.revert_to_checkpoint(vm, checkpoint)
            if not res.success:
                success = False
                env.last_error = f"Teardown failed on {vm}: {res.error}"
                break
        
        if success:
            env.status = "available"
            env.last_error = None
            # Delete the session
            db.query(LabSession).filter(LabSession.session_token == session_token).delete()
        else:
            env.status = "faulted"
            
    except Exception as e:
        logger.error(f"Teardown exception for {env_id}: {str(e)}")
        env.status = "faulted"
        env.last_error = str(e)
    
    db.commit()
    db.close()

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/lab/status")
async def get_status(db: Session = Depends(get_db)):
    envs = db.query(LabEnvironment).all()
    sessions = db.query(LabSession).all()
    return {
        "environments": [
            {"id": e.id, "status": e.status, "capabilities": e.capabilities, "updated_at": e.updated_at} 
            for e in envs
        ],
        "active_sessions": len(sessions)
    }

@app.post("/lab/provision/{scenario_id}", response_model=ProvisionResponse)
async def provision_lab(
    scenario_id: str, 
    req: ProvisionRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    # 1. Load scenario to verify it exists and get Mode E config
    scenarios_dir = Path(settings.scenarios_dir)
    scenario_path = scenarios_dir / f"{scenario_id.replace('-', '/')}/scenario.yaml"
    
    if not scenario_path.exists():
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found.")

    with open(scenario_path, 'r') as f:
        scenario = yaml.safe_load(f)

    mode_e = scenario.get('presentation', {}).get('modes', {}).get('E')
    if not mode_e:
        raise HTTPException(status_code=400, detail="Scenario does not support Mode E (Lab)")

    # 2. Find an available environment that matches capabilities
    # SQLite doesn't have SELECT FOR UPDATE but for this scale a simple status check is okay.
    # In production with multiple workers, we'd use a more robust locking mechanism.
    env = db.query(LabEnvironment).filter(
        LabEnvironment.status == "available"
    ).first()
    
    if not env:
        # TODO: Implement queueing. For now, 503.
        raise HTTPException(status_code=503, detail="No lab environments currently available. Please try again in a few minutes.")

    # 3. Lock the environment immediately (The Mutex)
    env.status = "provisioning"
    db.commit()

    # 4. Create Session
    session_token = str(uuid.uuid4())
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.session_timeout_minutes)
    max_expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.max_session_hours)
    
    new_session = LabSession(
        session_token=session_token,
        environment_id=env.id,
        user_id=req.user_id,
        scenario_id=scenario_id,
        expires_at=expires_at,
        max_expires_at=max_expires_at
    )
    db.add(new_session)
    db.commit()

    # 5. Run provisioning in background
    background_tasks.add_task(
        run_provisioning_flow, 
        env.id, 
        scenario_id, 
        mode_e, 
        session_token
    )

    # Note: Returning Guacamole URL immediately might be premature if it's still provisioning,
    # but the frontend will poll /status or handle the delay.
    # For now, we return the pre-configured Guac connection URL or similar.
    guac_url = f"{settings.guacamole_url}/#/client/{env.guac_connection_id}"

    return ProvisionResponse(
        status="provisioning",
        session_token=session_token,
        environment_id=env.id,
        guacamole_url=guac_url,
        expires_at=expires_at,
        instructions=mode_e.get('instructions', '')
    )

async def run_provisioning_flow(env_id: str, scenario_id: str, mode_e: dict, session_token: str):
    """The actual heavy lifting of reverting, starting, and configuring VMs."""
    db = next(get_db())
    env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
    
    try:
        checkpoint = mode_e.get('checkpoint', 'Baseline')
        vm_targets = env.vms # Use all VMs in the pool for this environment
        config = mode_e.get('config', {})
        provisioning_actions = config.get('provisioning', [])

        # 1. Revert & Start
        for vm in vm_targets:
            orchestrator.revert_to_checkpoint(vm, checkpoint)
            orchestrator.start_vm(vm)
        
        # 2. Wait for readiness
        for vm in vm_targets:
            orchestrator.wait_for_guest_readiness(vm)

        # 3. Provisioning Actions (Scripts, Files)
        # (Implementation same as previous main.py but mapping to correct VM targets)
        # ... logic omitted for brevity but would iterate actions ...

        env.status = "busy"
        env.last_error = None
    except Exception as e:
        logger.error(f"Provisioning failed for {env_id}: {str(e)}")
        env.status = "faulted"
        env.last_error = str(e)
    
    db.commit()
    db.close()

@app.post("/lab/renew/{session_token}")
async def renew_session(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already reaped.")
    
    now = datetime.datetime.utcnow()
    new_expiry = now + datetime.timedelta(minutes=30)
    
    # Cap at max_expires_at
    if new_expiry > session.max_expires_at:
        new_expiry = session.max_expires_at
        
    session.expires_at = new_expiry
    db.commit()
    
    return {"expires_at": session.expires_at}

@app.post("/lab/verify/{session_token}")
async def verify_lab(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found.")
    
    # TODO: Implement actual verification via scripts
    return [
        VerificationResult(
            finding_id="example", 
            status="correct", 
            detail="Verified successfully."
        )
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
