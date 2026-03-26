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
import json
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
    scheduler.add_job(reap_expired_sessions_wrapper, 'interval', minutes=1)
    scheduler.start()
    app.state.scheduler = scheduler

async def load_environments():
    """Seed or update the database with environments from config."""
    if not os.path.exists(settings.environments_config):
        logger.warning(f"Environments config {settings.environments_config} not found.")
        return

    with open(settings.environments_config, 'r') as f:
        config = yaml.safe_load(f)
    
    with session_scope() as db:
        # Before seeding, if we are rebooting, we should reset any 
        # non-terminal state to its default from the YAML.
        # This prevents environments being stuck in 'provisioning' forever after a crash.
        db.query(LabSession).delete() # Flush sessions on restart as Hyper-V state is unknown

        for env_data in config.get('environments', []):
            existing = db.query(LabEnvironment).filter(LabEnvironment.id == env_data['id']).first()
            target_status = env_data.get('status', "available")
            
            if not existing:
                env = LabEnvironment(
                    id=env_data['id'],
                    vms=env_data['vms'],
                    guac_connection_id=env_data['guac_connection_id'],
                    capabilities=env_data['capabilities'],
                    status=target_status
                )
                db.add(env)
            else:
                # Update capabilities/VMS from config
                existing.vms = env_data['vms']
                existing.capabilities = env_data['capabilities']
                existing.guac_connection_id = env_data['guac_connection_id']
                # Reset status to available/default on reboot to ensure health
                if existing.status not in ["available", "faulted"]:
                    existing.status = target_status

# ---------------------------------------------------------------------------
# Reaper & Teardown
# ---------------------------------------------------------------------------

def reap_expired_sessions_wrapper():
    """Sync wrapper for async reaper."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(reap_expired_sessions())

async def reap_expired_sessions():
    """Background task to clean up expired lab environments."""
    now = datetime.datetime.utcnow()
    
    with session_scope() as db:
        expired = db.query(LabSession).filter(LabSession.expires_at < now).all()
        for session in expired:
            logger.info(f"Reaping expired session {session.session_token} for env {session.environment_id}")
            await teardown_environment_logic(session.environment_id, session.session_token)

async def teardown_environment_logic(env_id: str, session_token: str):
    """Reverts VMs and marks environment as available."""
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if not env:
            return

        env.status = "teardown"
        db.commit()

        try:
            checkpoint = "Baseline" 
            success = True
            for vm in env.vms:
                res = await orchestrator.revert_to_checkpoint(vm, checkpoint)
                if not res.success:
                    success = False
                    env.last_error = f"Teardown failed on {vm}: {res.error}"
                    break
            
            if success:
                env.status = "available"
                env.last_error = None
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
    if not re.match(r'^[a-z0-9\-]+$', scenario_id):
        raise HTTPException(status_code=400, detail="Invalid scenario_id format.")
    return scenario_id

def resolve_scenario_path(scenario_id: str) -> Path:
    scenarios_dir = Path(settings.scenarios_dir).resolve()
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

    # 1. Capability Matching
    required_capabilities = mode_e.get('capabilities', [])
    
    # Filter available environments by capabilities
    available_envs = db.query(LabEnvironment).filter(LabEnvironment.status == "available").all()
    
    selected_env = None
    for env in available_envs:
        # Check if environment has all required capabilities
        env_caps = set(env.capabilities or [])
        if all(cap in env_caps for cap in required_capabilities):
            selected_env = env
            break
            
    if not selected_env:
        raise HTTPException(status_code=503, detail="No capable lab environments currently available.")

    # 2. Atomic Mutex
    affected = db.query(LabEnvironment).filter(
        LabEnvironment.id == selected_env.id,
        LabEnvironment.status == "available"
    ).update({"status": "provisioning"})
    
    if affected == 0:
        db.rollback()
        raise HTTPException(status_code=503, detail="Contention detected. Please retry.")
    
    db.commit()

    # 3. Create Session
    session_token = str(uuid.uuid4())
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.session_timeout_minutes)
    max_expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.max_session_hours)
    
    new_session = LabSession(
        session_token=session_token,
        environment_id=selected_env.id,
        user_id=req.user_id,
        scenario_id=scenario_id,
        expires_at=expires_at,
        max_expires_at=max_expires_at
    )
    db.add(new_session)
    db.commit()

    # 4. Background Provisioning
    background_tasks.add_task(
        run_provisioning_flow, 
        selected_env.id, 
        scenario_path, 
        mode_e, 
        session_token
    )

    guac_url = f"{settings.guacamole_url}/#/client/{selected_env.guac_connection_id}"

    return ProvisionResponse(
        status="provisioning",
        session_token=session_token,
        environment_id=selected_env.id,
        guacamole_url=guac_url,
        expires_at=expires_at,
        instructions=mode_e.get('instructions', '')
    )

async def run_provisioning_flow(env_id: str, scenario_path: Path, mode_e: dict, session_token: str):
    try:
        checkpoint = mode_e.get('checkpoint', 'Baseline')
        config = mode_e.get('config', {})
        provisioning_actions = config.get('provisioning', []) if config else []
        
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if not env: return
            vm_targets = env.vms

            for vm in vm_targets:
                await orchestrator.revert_to_checkpoint(vm, checkpoint)
                await orchestrator.start_vm(vm)
            
            for vm in vm_targets:
                await orchestrator.wait_for_guest_readiness(vm)

            for action in provisioning_actions:
                target = action.get('target')
                act_type = action.get('action')
                if act_type == "run_script":
                    script_path = scenario_path.parent / action.get('file')
                    await orchestrator.run_script_in_guest(target, str(script_path))
                elif act_type == "copy_file":
                    src = scenario_path.parent / action.get('source')
                    await orchestrator.copy_file_to_guest(target, str(src), action.get('destination'))

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
    session.expires_at = min(now + datetime.timedelta(minutes=30), session.max_expires_at)
    db.commit()
    return {"expires_at": session.expires_at}

@app.post("/lab/verify/{session_token}")
async def verify_lab(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found.")
    
    scenario_id = session.scenario_id
    scenario_path = resolve_scenario_path(scenario_id)
    with open(scenario_path, 'r') as f:
        scenario = yaml.safe_load(f)
    
    mode_e = scenario.get('presentation', {}).get('modes', {}).get('E', {})
    config = mode_e.get('config', {})
    verification_steps = config.get('verification', [])
    
    results = []
    for step in verification_steps:
        target = step.get('target')
        script_path = scenario_path.parent / step.get('file')
        finding_id = step.get('finding_id')
        
        res = await orchestrator.run_script_in_guest(target, str(script_path))
        if res.success:
            try:
                parsed = json.loads(res.output)
                results.append(VerificationResult(finding_id=finding_id, status=parsed.get('status', 'incomplete'), detail=parsed.get('detail', '')))
            except:
                results.append(VerificationResult(finding_id=finding_id, status="incomplete", detail="Verification script output could not be parsed."))
        else:
            results.append(VerificationResult(finding_id=finding_id, status="incomplete", detail=f"Verification script failed: {res.error}"))
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
