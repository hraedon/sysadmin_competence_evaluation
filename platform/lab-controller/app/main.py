from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import yaml
import os
import datetime
import uuid
import logging
import re
import asyncio
from pathlib import Path
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from .orchestrator import HyperVOrchestrator
from .guacamole import GuacamoleClient
from .database import init_db, get_db, session_scope, LabEnvironment, LabSession
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
async def startup_event():
    init_db()
    await load_environments()
    
    # Start the reaper
    scheduler = BackgroundScheduler()
    # Note: reaper needs to be async-aware or run in a thread
    scheduler.add_job(reap_expired_sessions_wrapper, 'interval', minutes=1)
    scheduler.start()
    app.state.scheduler = scheduler

async def load_environments():
    """Seed the database with environments from config if not already present."""
    if not os.path.exists(settings.environments_config):
        logger.warning(f"Environments config {settings.environments_config} not found.")
        return

    with open(settings.environments_config, 'r') as f:
        config = yaml.safe_load(f)
    
    with session_scope() as db:
        for env_data in config.get('environments', []):
            existing = db.query(LabEnvironment).filter(LabEnvironment.id == env_data['id']).first()
            if not existing:
                env = LabEnvironment(
                    id=env_data['id'],
                    vms=env_data['vms'],
                    guac_connection_id=env_data['guac_connection_id'],
                    capabilities=env_data['capabilities'],
                    status=env_data.get('status', "available")
                )
                db.add(env)

# ---------------------------------------------------------------------------
# Reaper & Teardown
# ---------------------------------------------------------------------------

def reap_expired_sessions_wrapper():
    """Sync wrapper for async reaper."""
    asyncio.run(reap_expired_sessions())

async def reap_expired_sessions():
    """Background task to clean up expired lab environments."""
    now = datetime.datetime.utcnow()
    
    with session_scope() as db:
        expired = db.query(LabSession).filter(LabSession.expires_at < now).all()
        for session in expired:
            logger.info(f"Reaping expired session {session.session_token} for env {session.environment_id}")
            # We trigger teardown but we need to be careful about async from sync reaper
            # For now we'll do it sequentially in this background task
            await teardown_environment_logic(session.environment_id, session.session_token)

async def teardown_environment_logic(env_id: str, session_token: str):
    """Reverts VMs and marks environment as available."""
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if not env:
            return

        env.status = "teardown"
        db.commit() # Commit status change immediately

        try:
            checkpoint = "Baseline" 
            success = True
            for vm in env.vms:
                logger.info(f"Teardown: Reverting {vm}")
                res = await orchestrator.revert_to_checkpoint(vm, checkpoint)
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

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sanitize_scenario_id(scenario_id: str) -> str:
    """Validate and sanitize scenario_id to prevent path traversal."""
    if not re.match(r'^[a-z0-9\-]+$', scenario_id):
        raise HTTPException(status_code=400, detail="Invalid scenario_id format.")
    return scenario_id

def resolve_scenario_path(scenario_id: str) -> Path:
    """Resolve scenario_id to a file path, ensuring it stays within scenarios_dir."""
    scenarios_dir = Path(settings.scenarios_dir).resolve()
    # Standard convention: dXX-name-here -> dXX/name_here/scenario.yaml
    # But current data uses hyphens in IDs that map to underscores in dirs sometimes.
    # We'll use the ID-to-path logic from the current implementation but sanitize.
    rel_path = scenario_id.replace('-', '/')
    scenario_path = (scenarios_dir / rel_path / "scenario.yaml").resolve()
    
    if not str(scenario_path).startswith(str(scenarios_dir)):
        raise HTTPException(status_code=400, detail="Invalid scenario_id path.")
    
    return scenario_path

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
            {"id": e.id, "status": e.status, "capabilities": e.capabilities, "updated_at": e.updated_at, "last_error": e.last_error} 
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
    scenario_id = sanitize_scenario_id(scenario_id)
    scenario_path = resolve_scenario_path(scenario_id)
    
    if not scenario_path.exists():
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found.")

    with open(scenario_path, 'r') as f:
        scenario = yaml.safe_load(f)

    mode_e = scenario.get('presentation', {}).get('modes', {}).get('E')
    if not mode_e:
        raise HTTPException(status_code=400, detail="Scenario does not support Mode E (Lab)")

    # 1. Atomic search-and-lock
    # We use a transaction and an immediate update to ensure we own the environment.
    # SQLite doesn't have SELECT FOR UPDATE, so we update status and check if it worked.
    env = db.query(LabEnvironment).filter(LabEnvironment.status == "available").first()
    if not env:
        raise HTTPException(status_code=503, detail="No lab environments currently available.")

    # Mutex: Update status to provisioning only if it's still available
    affected = db.query(LabEnvironment).filter(
        LabEnvironment.id == env.id,
        LabEnvironment.status == "available"
    ).update({"status": "provisioning"})
    
    if affected == 0:
        # Someone else grabbed it between our SELECT and UPDATE
        db.rollback()
        raise HTTPException(status_code=503, detail="Contention detected. Please retry.")
    
    db.commit()

    # 2. Create Session
    session_token = str(uuid.uuid4())
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.session_timeout_minutes)
    max_expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.max_session_hours)
    
    new_session = LabSession(
        session_token=session_token,
        environment_id=env.id,
        user_id=req.id if hasattr(req, 'id') else req.user_id, # Handle minor model mismatch
        scenario_id=scenario_id,
        expires_at=expires_at,
        max_expires_at=max_expires_at
    )
    db.add(new_session)
    db.commit()

    # 3. Run provisioning in background
    # BackgroundTasks handles async def correctly
    background_tasks.add_task(
        run_provisioning_flow, 
        env.id, 
        scenario_path, 
        mode_e, 
        session_token
    )

    guac_url = f"{settings.guacamole_url}/#/client/{env.guac_connection_id}"

    return ProvisionResponse(
        status="provisioning",
        session_token=session_token,
        environment_id=env.id,
        guacamole_url=guac_url,
        expires_at=expires_at,
        instructions=mode_e.get('instructions', '')
    )

async def run_provisioning_flow(env_id: str, scenario_path: Path, mode_e: dict, session_token: str):
    """The actual heavy lifting of reverting, starting, and configuring VMs."""
    try:
        checkpoint = mode_e.get('checkpoint', 'Baseline')
        config = mode_e.get('config', {})
        provisioning_actions = config.get('provisioning', []) if config else []
        
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if not env: return
            vm_targets = env.vms

            # 1. Revert & Start
            for vm in vm_targets:
                await orchestrator.revert_to_checkpoint(vm, checkpoint)
                await orchestrator.start_vm(vm)
            
            # 2. Wait for readiness
            for vm in vm_targets:
                await orchestrator.wait_for_guest_readiness(vm)

            # 3. Provisioning Actions (Scripts, Files)
            for action in provisioning_actions:
                target = action.get('target')
                act_type = action.get('action')
                
                if act_type == "run_script":
                    script_file = action.get('file')
                    script_path = scenario_path.parent / script_file
                    await orchestrator.run_script_in_guest(target, str(script_path))
                elif act_type == "copy_file":
                    src = scenario_path.parent / action.get('source')
                    dest = action.get('destination')
                    await orchestrator.copy_file_to_guest(target, str(src), dest)

            env.status = "busy"
            env.last_error = None
    except Exception as e:
        logger.error(f"Provisioning failed for {env_id}: {str(e)}")
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if env:
                env.status = "faulted"
                env.last_error = str(e)

@app.post("/lab/renew/{session_token}")
async def renew_session(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    now = datetime.datetime.utcnow()
    # Renewal adds 30m from now, up to the max cap
    session.expires_at = min(now + datetime.timedelta(minutes=30), session.max_expires_at)
    db.commit()
    
    return {"expires_at": session.expires_at}

@app.post("/lab/verify/{session_token}")
async def verify_lab(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found.")
    
    # 1. Resolve scenario path to find verification scripts
    scenario_id = session.scenario_id
    scenario_path = resolve_scenario_path(scenario_id)
    
    with open(scenario_path, 'r') as f:
        scenario = yaml.safe_load(f)
    
    mode_e = scenario.get('presentation', {}).get('modes', {}).get('E', {})
    config = mode_e.get('config', {})
    verification_steps = config.get('verification', [])
    
    env = db.query(LabEnvironment).filter(LabEnvironment.id == session.environment_id).first()
    
    results = []
    for step in verification_steps:
        target = step.get('target')
        script_file = step.get('file')
        finding_id = step.get('finding_id')
        
        script_path = scenario_path.parent / script_file
        res = await orchestrator.run_script_in_guest(target, str(script_path))
        
        if res.success:
            try:
                # Expecting JSON output from the script
                parsed = json.loads(res.output)
                results.append(VerificationResult(
                    finding_id=finding_id,
                    status=parsed.get('status', 'incomplete'),
                    detail=parsed.get('detail', '')
                ))
            except:
                results.append(VerificationResult(
                    finding_id=finding_id,
                    status="incomplete",
                    detail="Verification script output could not be parsed."
                ))
        else:
            results.append(VerificationResult(
                finding_id=finding_id,
                status="incomplete",
                detail=f"Verification script failed: {res.error}"
            ))
            
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
