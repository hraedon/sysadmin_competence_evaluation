from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
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
from .evaluator import perform_evaluation
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Settings & Configuration
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    guacamole_url: str = "http://localhost:8080/guacamole"
    guacamole_username: str = ""
    guacamole_password: str = ""
    scenarios_dir: str = "/scenarios"
    environments_config: str = "environments.yaml"
    session_timeout_minutes: int = 120
    max_session_hours: int = 4
    provisioning_timeout_seconds: int = 600  # 10 min outer watchdog for entire provisioning flow
    dry_run: bool = True
    # Hyper-V host credentials for WinRM remoting (used by HyperVOrchestrator)
    hyperv_host: str = "mvmhyperv02.ad.hraedon.com"
    hyperv_username: str = "svc_claude@ad.hraedon.com"
    hyperv_password: str = ""
    # Guest OS credentials for PowerShell Direct (lab domain admin)
    hyperv_guest_username: str = "ad.labdomain.dev\\claude"
    hyperv_guest_password: str = ""
    controller_api_key: str = "dev-key-change-me"
    anthropic_api_key: str = ""
    # Reconciler settings
    reconcile_interval_minutes: int = 5         # how often the reconciler runs
    fault_auto_retry_delay_minutes: int = 10    # min time between fault and first auto-retry
    fault_max_auto_retries: int = 2             # give up after this many failed auto-recoveries
    # NOTE: teardown hardcodes "Baseline" but scenario YAML can specify a different checkpoint
    # name (e.g., "Baseline Checkpoint"). This setting is the fallback used by teardown and the
    # reconciler. Set it to match the actual snapshot name on your Hyper-V VMs.
    baseline_checkpoint_name: str = "Baseline"

    class Config:
        env_file = ".env"

settings = Settings()

# ---------------------------------------------------------------------------
# Auth Dependency
# ---------------------------------------------------------------------------

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.controller_api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

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
    guacamole_url: Optional[str] = None  # SEC-02: populated by polling endpoint after ephemeral connection is created
    expires_at: datetime.datetime
    instructions: str

class VerificationResult(BaseModel):
    finding_id: str
    status: str  # correct | workaround | incomplete
    detail: str

class EvaluateRequest(BaseModel):
    scenario: Dict[str, Any]
    artifactContent: Optional[str] = None
    responseText: str
    model: Optional[str] = None
    coachMode: bool = False
    coachRound: int = 0
    coachHistory: List[Dict[str, str]] = []
    compactRubric: bool = False

# ---------------------------------------------------------------------------
# Lifecycle & Initialization
# ---------------------------------------------------------------------------

app = FastAPI(title="Sysadmin Competency Lab Controller")
orchestrator = HyperVOrchestrator(
    host=settings.hyperv_host,
    username=settings.hyperv_username,
    password=settings.hyperv_password,
    guest_username=settings.hyperv_guest_username,
    guest_password=settings.hyperv_guest_password,
    dry_run=settings.dry_run,
)
guac_client = GuacamoleClient(
    settings.guacamole_url, 
    settings.guacamole_username, 
    settings.guacamole_password
)

@app.on_event("startup")
async def startup_event():
    init_db()
    await load_environments()
    
    # Start background jobs
    scheduler = BackgroundScheduler()
    scheduler.add_job(reap_expired_sessions_wrapper, 'interval', minutes=1)
    scheduler.add_job(reconcile_environments_wrapper, 'interval', minutes=settings.reconcile_interval_minutes)
    scheduler.start()
    app.state.scheduler = scheduler

async def load_environments():
    """Seed or update the database with environments from config.

    ARCH-02: Instead of deleting all sessions on restart (which orphans
    partially-provisioned VMs), we mark surviving sessions as 'suspect'.
    The reaper will attempt graceful teardown on suspect sessions before
    deleting them, so the associated environments can return to 'available'.
    """
    if not os.path.exists(settings.environments_config):
        logger.warning(f"Environments config {settings.environments_config} not found.")
        return

    with open(settings.environments_config, 'r') as f:
        config = yaml.safe_load(f)

    with session_scope() as db:
        # Mark all existing sessions as suspect so the reaper can attempt
        # graceful teardown rather than just losing track of them.
        orphaned = db.query(LabSession).all()
        for sess in orphaned:
            sess.suspect = True
            # Force expiry so the reaper picks them up on its next tick
            sess.expires_at = datetime.datetime.utcnow()
            logger.info(f"Marked session {sess.session_token} as suspect (restart recovery)")

        for env_data in config.get('environments', []):
            existing = db.query(LabEnvironment).filter(LabEnvironment.id == env_data['id']).first()
            target_status = env_data.get('status', "available")

            if not existing:
                env = LabEnvironment(
                    id=env_data['id'],
                    vms=env_data['vms'],
                    guac_connection_id=env_data['guac_connection_id'],
                    guac_target_vm=env_data.get('guac_target_vm'),
                    guac_protocol=env_data.get('guac_protocol'),
                    capabilities=env_data['capabilities'],
                    status=target_status
                )
                db.add(env)
            else:
                # Update capabilities/VMS from config
                existing.vms = env_data['vms']
                existing.capabilities = env_data['capabilities']
                existing.guac_connection_id = env_data['guac_connection_id']
                existing.guac_target_vm = env_data.get('guac_target_vm')
                existing.guac_protocol = env_data.get('guac_protocol')
                # Reset status to available/default on reboot to ensure health
                if existing.status not in ["available", "faulted"]:
                    existing.status = target_status

# ---------------------------------------------------------------------------
# Reaper & Teardown
# ---------------------------------------------------------------------------

def reap_expired_sessions_wrapper():
    """Sync wrapper for async reaper.

    Uses asyncio.run() instead of the deprecated get_event_loop() pattern.
    Each invocation gets a fresh event loop, which is correct since
    BackgroundScheduler calls this from a thread-pool thread.
    """
    asyncio.run(reap_expired_sessions())

def reconcile_environments_wrapper():
    """Sync wrapper for async reconciler (same pattern as reaper wrapper)."""
    asyncio.run(reconcile_environments())

async def reap_expired_sessions():
    """Background task to clean up expired lab environments."""
    now = datetime.datetime.utcnow()

    # Collect expired sessions in a short-lived DB session, then teardown outside the lock
    with session_scope() as db:
        expired = db.query(LabSession).filter(LabSession.expires_at < now).all()
        expired_pairs = [(s.environment_id, s.session_token) for s in expired]

    for env_id, token in expired_pairs:
        logger.info(f"Reaping expired session {token} for env {env_id}")
        await teardown_environment_logic(env_id, token)

async def _attempt_auto_recovery(env_id: str, vm_list: list):
    """Revert each VM in the environment to the Baseline checkpoint.

    On success: resets environment to 'available' and clears all fault state.
    On failure: increments fault_retry_count and resets faulted_at so the
                reconciler won't retry again until the delay has elapsed.
    """
    checkpoint = settings.baseline_checkpoint_name
    success = True
    last_error = None
    for vm in vm_list:
        res = await orchestrator.revert_to_checkpoint(vm, checkpoint)
        if not res.success:
            success = False
            last_error = f"Auto-recovery revert failed for '{vm}': {res.error}"
            # Attempt all VMs even if one fails

    if success:
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if env:
                env.status = "available"
                env.last_error = None
                env.provision_step = None
                env.faulted_at = None
                env.fault_retry_count = 0
        logger.info(f"Reconciler: auto-recovered env '{env_id}' — returned to 'available'")
    else:
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if env:
                env.fault_retry_count = (env.fault_retry_count or 0) + 1
                env.faulted_at = datetime.datetime.utcnow()  # reset timer for next retry window
                env.last_error = last_error
        logger.warning(f"Reconciler: auto-recovery failed for '{env_id}': {last_error}")


async def reconcile_environments():
    """Periodic reconciler: detect and repair out-of-compliance lab environments.

    Runs every RECONCILE_INTERVAL_MINUTES (default: 5).  Two jobs:

    Phase 1 — Fault auto-retry:
        Find faulted environments where faulted_at is old enough AND
        fault_retry_count < fault_max_auto_retries.  Attempt to revert
        each VM to the Baseline checkpoint and reset the environment to
        'available'.  Stops retrying after fault_max_auto_retries failures;
        at that point operator intervention (admin reset) is required.

    Phase 2 — Orphan VM detection (skipped in dry_run):
        Query the Hyper-V host for the actual VM power state of every
        'available' environment.  If any VM is Running/Saved/Paused but
        no session owns it, revert to Baseline.  This catches VMs that
        were left running by a crash mid-provisioning before a session
        record was created.

    Does NOT touch: busy / provisioning / teardown environments.
    """
    now = datetime.datetime.utcnow()
    retry_cutoff = now - datetime.timedelta(minutes=settings.fault_auto_retry_delay_minutes)

    # --- Phase 1: retry eligible faulted environments ---
    with session_scope() as db:
        faulted_envs = db.query(LabEnvironment).filter(
            LabEnvironment.status == "faulted",
            LabEnvironment.fault_retry_count < settings.fault_max_auto_retries,
        ).all()
        # Only pick up envs whose faulted_at is old enough (or not set yet)
        eligible = [
            (e.id, list(e.vms))
            for e in faulted_envs
            if e.faulted_at is None or e.faulted_at <= retry_cutoff
        ]

    for env_id, vm_list in eligible:
        logger.info(f"Reconciler: attempting auto-recovery for faulted env '{env_id}'")
        await _attempt_auto_recovery(env_id, vm_list)

    # --- Phase 2: orphan VM detection (requires WinRM — skip in dry_run) ---
    if settings.dry_run:
        return

    with session_scope() as db:
        available_envs = db.query(LabEnvironment).filter(
            LabEnvironment.status == "available"
        ).all()
        available_list = [(e.id, list(e.vms)) for e in available_envs]

    for env_id, vm_list in available_list:
        for vm in vm_list:
            state_res = await orchestrator.get_vm_state(vm)
            if not state_res.success:
                logger.warning(
                    f"Reconciler: could not query state of VM '{vm}' "
                    f"in env '{env_id}': {state_res.error}"
                )
                continue
            vm_state = state_res.output.strip().lower()
            if vm_state != "off":
                logger.warning(
                    f"Reconciler: orphan VM '{vm}' in env '{env_id}' is '{vm_state}' "
                    f"but environment shows 'available'. Reverting to Baseline."
                )
                revert_res = await orchestrator.revert_to_checkpoint(
                    vm, settings.baseline_checkpoint_name
                )
                if not revert_res.success:
                    logger.error(
                        f"Reconciler: failed to revert orphan VM '{vm}': {revert_res.error}"
                    )
                    _update_env_status(
                        env_id, "faulted",
                        last_error=f"Orphan VM revert failed for '{vm}': {revert_res.error}"
                    )


async def teardown_environment_logic(env_id: str, session_token: str):
    """Reverts VMs and marks environment as available. Deletes dynamic Guacamole connections.

    Uses short-lived DB sessions per step to avoid holding SQLite locks across
    async operations (same pattern as run_provisioning_flow).
    """
    # Read what we need and mark as teardown (short-lived session)
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if not env:
            return
        vm_list = list(env.vms)  # copy before session closes
        env.status = "teardown"

    # Read Guacamole connection ID from session (separate short-lived session)
    guac_conn_id = None
    with session_scope() as db:
        session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
        if session and session.guac_connection_id:
            guac_conn_id = session.guac_connection_id

    # Delete dynamic Guacamole connection (no DB lock held)
    if guac_conn_id:
        try:
            await guac_client.delete_connection(guac_conn_id)
        except Exception as e:
            logger.error(f"Failed to delete Guacamole connection {guac_conn_id}: {str(e)}")

    # Revert VMs (no DB lock held)
    try:
        checkpoint = settings.baseline_checkpoint_name
        success = True
        last_error = None
        for vm in vm_list:
            res = await orchestrator.revert_to_checkpoint(vm, checkpoint)
            if not res.success:
                success = False
                last_error = f"Teardown failed on {vm}: {res.error}"
                # Don't break; try to revert others to be safe

        # Update final status (short-lived session)
        _update_env_status(
            env_id,
            "available" if success else "faulted",
            last_error=last_error
        )
    except Exception as e:
        logger.error(f"Teardown exception for {env_id}: {str(e)}")
        _update_env_status(env_id, "faulted", last_error=str(e))
    finally:
        # ALWAYS delete the session record so the environment isn't permanently locked
        with session_scope() as db:
            db.query(LabSession).filter(LabSession.session_token == session_token).delete()

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sanitize_scenario_id(scenario_id: str) -> str:
    if not re.match(r'^[a-z0-9\-]+$', scenario_id):
        raise HTTPException(status_code=400, detail="Invalid scenario_id format.")
    return scenario_id

def resolve_scenario_path(scenario_id: str) -> Path:
    scenarios_dir = Path(settings.scenarios_dir).resolve()
    
    # Expected format: dXX-scenario-name
    # Maps to: dXX/scenario_name/scenario.yaml
    parts = scenario_id.split('-', 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid scenario_id format. Expected dXX-name.")
    
    domain_dir = parts[0]
    scenario_folder = parts[1].replace('-', '_')
    
    scenario_path = (scenarios_dir / domain_dir / scenario_folder / "scenario.yaml").resolve()
    
    if not str(scenario_path).startswith(str(scenarios_dir)):
        raise HTTPException(status_code=400, detail="Invalid scenario_id path.")
    return scenario_path

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
@app.get("/lab/health")
async def health_check(db: Session = Depends(get_db)):
    envs = db.query(LabEnvironment).all()
    faulted = [e.id for e in envs if e.status == "faulted"]
    available = sum(1 for e in envs if e.status == "available")
    # Include per-fault retry info so operators can see if auto-recovery is spinning
    faulted_detail = [
        {"id": e.id, "last_error": e.last_error,
         "fault_retry_count": e.fault_retry_count or 0,
         "faulted_at": e.faulted_at.isoformat() if e.faulted_at else None}
        for e in envs if e.status == "faulted"
    ]
    return {
        "status": "degraded" if faulted else "healthy",
        "environments_total": len(envs),
        "environments_available": available,
        "environments_faulted": faulted_detail,
    }

@app.get("/lab/status", dependencies=[Depends(verify_api_key)])
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

@app.post("/lab/provision/{scenario_id}", response_model=ProvisionResponse, dependencies=[Depends(verify_api_key)])
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
        all_envs = db.query(LabEnvironment).all()
        if not all_envs:
            detail = "No lab environments configured. Verify environments.yaml was loaded at startup."
        elif not available_envs:
            faulted_ids = [e.id for e in all_envs if e.status == "faulted"]
            active_ids = [e.id for e in all_envs if e.status in ("busy", "provisioning", "teardown")]
            parts = []
            if faulted_ids:
                parts.append(f"{len(faulted_ids)} faulted {faulted_ids} — reset via POST /lab/admin/reset-all-faulted")
            if active_ids:
                parts.append(f"{len(active_ids)} active {active_ids}")
            detail = "No available environments. " + "; ".join(parts)
        else:
            caps_available = [sorted(e.capabilities or []) for e in available_envs]
            detail = (
                f"No available environment supports capabilities {sorted(required_capabilities)}. "
                f"Available environments offer: {caps_available}"
            )
        raise HTTPException(status_code=503, detail=detail)

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

    # 4. Background Provisioning (with watchdog timeout)
    background_tasks.add_task(
        run_provisioning_with_watchdog,
        selected_env.id,
        scenario_path,
        mode_e,
        session_token
    )

    # SEC-02: Don't return a Guacamole URL here. The ephemeral connection
    # is created during provisioning and served via GET /lab/session/{token}.
    return ProvisionResponse(
        status="provisioning",
        session_token=session_token,
        environment_id=selected_env.id,
        expires_at=expires_at,
        instructions=mode_e.get('instructions', '')
    )

def _update_provision_step(env_id: str, step: str):
    """Update the current provisioning step using a short-lived DB session.

    Each call opens and commits its own session so the change is immediately
    visible to concurrent readers (the session-polling endpoint).
    """
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if env:
            env.provision_step = step
            env.provision_step_updated_at = datetime.datetime.utcnow()

def _update_env_status(env_id: str, status: str, provision_step=None, last_error=None):
    """Update environment status using a short-lived DB session.

    Side effects:
    - When status transitions TO 'faulted': stamps faulted_at (if not already set)
      and preserves existing fault_retry_count so the reconciler can track attempts.
    - When status transitions TO 'available': clears faulted_at and fault_retry_count.
    """
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if env:
            env.status = status
            env.provision_step = provision_step
            env.provision_step_updated_at = None
            env.last_error = last_error
            if status == "faulted":
                if not env.faulted_at:
                    env.faulted_at = datetime.datetime.utcnow()
                # fault_retry_count is left unchanged — reconciler manages it
            elif status == "available":
                env.faulted_at = None
                env.fault_retry_count = 0

def _reset_environment(env_id: str) -> str:
    """Reset a non-active environment to 'available' and clear its fault state.

    Returns the previous status string.
    Raises HTTPException(404) if not found.
    Raises HTTPException(409) if the environment is actively provisioning or in use —
    resetting an active environment would orphan the running VM.
    """
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if not env:
            raise HTTPException(status_code=404, detail=f"Environment '{env_id}' not found.")
        if env.status in ("provisioning", "busy", "teardown"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reset '{env_id}': currently '{env.status}'. "
                       f"Only faulted or available environments may be reset."
            )
        previous = env.status
        env.status = "available"
        env.last_error = None
        env.provision_step = None
        env.faulted_at = None
        env.fault_retry_count = 0
    return previous

def _reset_all_faulted() -> List[str]:
    """Reset every faulted environment to 'available'. Returns the list of reset env IDs."""
    with session_scope() as db:
        faulted = db.query(LabEnvironment).filter(LabEnvironment.status == "faulted").all()
        reset_ids = [e.id for e in faulted]
        for env in faulted:
            env.status = "available"
            env.last_error = None
            env.provision_step = None
            env.faulted_at = None
            env.fault_retry_count = 0
    return reset_ids

async def run_provisioning_with_watchdog(env_id: str, scenario_path: Path, mode_e: dict, session_token: str):
    """Outer watchdog that ensures provisioning cannot run indefinitely."""
    try:
        await asyncio.wait_for(
            run_provisioning_flow(env_id, scenario_path, mode_e, session_token),
            timeout=settings.provisioning_timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.error(f"Provisioning watchdog timeout ({settings.provisioning_timeout_seconds}s) for {env_id}")
        _update_env_status(env_id, "faulted", last_error=f"Provisioning timed out after {settings.provisioning_timeout_seconds}s")

async def run_provisioning_flow(env_id: str, scenario_path: Path, mode_e: dict, session_token: str):
    try:
        checkpoint = mode_e.get('checkpoint', 'Baseline')
        config = mode_e.get('config', {})
        provisioning_actions = config.get('provisioning', []) if config else []

        # Read environment config once (short-lived session)
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if not env: return
            vm_targets = list(env.vms)  # copy — session closes after this block
            guac_target_vm = env.guac_target_vm
            guac_protocol = env.guac_protocol

        _update_provision_step(env_id, "reverting")
        for vm in vm_targets:
            result = await orchestrator.revert_to_checkpoint(vm, checkpoint)
            if not result.success:
                raise Exception(f"Checkpoint revert failed for {vm}: {result.error}")

        _update_provision_step(env_id, "starting")
        for vm in vm_targets:
            result = await orchestrator.start_vm(vm)
            if not result.success:
                raise Exception(f"VM start failed for {vm}: {result.error}")

        _update_provision_step(env_id, "waiting_ip")
        async def _on_connectivity():
            _update_provision_step(env_id, "testing_connectivity")
        for vm in vm_targets:
            ready = await orchestrator.wait_for_guest_readiness(vm, on_connectivity_phase=_on_connectivity)
            if not ready:
                raise Exception(f"Timeout waiting for {vm} to become ready (IP + connectivity)")

        # Create dynamic Guacamole connection
        _update_provision_step(env_id, "creating_guac")
        if guac_target_vm and guac_protocol:
            ip_res = await orchestrator.get_vm_ip(guac_target_vm)
            if ip_res.success and ip_res.output:
                params = {
                    "hostname": ip_res.output,
                    "username": "labuser",
                    "password": settings.hyperv_guest_password
                }
                if guac_protocol == "rdp":
                    params["ignore-cert"] = "true"
                    params["security"] = "any"

                conn_name = f"Session-{session_token[:8]}"
                guac_id, guac_url = await guac_client.create_connection(
                    name=conn_name,
                    protocol=guac_protocol,
                    parameters=params
                )

                with session_scope() as db:
                    sess = db.query(LabSession).filter(LabSession.session_token == session_token).first()
                    if sess:
                        sess.guac_connection_id = guac_id

        _update_provision_step(env_id, "running_scripts")
        for action in provisioning_actions:
            target = action.get('target')
            act_type = action.get('action')
            res = None
            if act_type == "run_script":
                script_path = scenario_path.parent / action.get('file')
                res = await orchestrator.run_script_in_guest(target, str(script_path))
            elif act_type == "copy_file":
                src = scenario_path.parent / action.get('source')
                res = await orchestrator.copy_file_to_guest(target, str(src), action.get('destination'))

            if res and not res.success:
                logger.error(f"Action {act_type} failed on {target}: {res.error}")
                raise Exception(f"Provisioning action failed: {res.error}")

        _update_env_status(env_id, "busy")
    except Exception as e:
        logger.error(f"Provisioning failed for {env_id}: {str(e)}")
        _update_env_status(env_id, "faulted", last_error=str(e))

@app.get("/lab/session/{session_token}", dependencies=[Depends(verify_api_key)])
async def get_session_status(session_token: str, db: Session = Depends(get_db)):
    """Returns the current status of a lab session and its environment."""
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    env = db.query(LabEnvironment).filter(LabEnvironment.id == session.environment_id).first()
    
    if not guac_client.token:
        try:
            await guac_client._authenticate()
        except:
            pass # Continue with unauthenticated URL if API is down

    # SEC-02: Only use ephemeral per-session connection IDs, never static ones.
    guacamole_url = None
    if session.guac_connection_id:
        guacamole_url = guac_client._client_url(session.guac_connection_id)

    return {
        "session_token": session_token,
        "scenario_id": session.scenario_id,
        "environment_id": session.environment_id,
        "environment_status": env.status if env else "unknown",
        "provision_step": env.provision_step if env else None,
        "provision_step_updated_at": env.provision_step_updated_at.isoformat() if env and env.provision_step_updated_at else None,
        "expires_at": session.expires_at,
        "guacamole_url": guacamole_url
    }

@app.post("/lab/renew/{session_token}", dependencies=[Depends(verify_api_key)])
async def renew_session(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    now = datetime.datetime.utcnow()
    session.expires_at = min(now + datetime.timedelta(minutes=30), session.max_expires_at)
    db.commit()
    return {"expires_at": session.expires_at}

@app.post("/lab/teardown/{session_token}", dependencies=[Depends(verify_api_key)])
async def teardown_lab(session_token: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Explicitly ends a lab session and triggers environment teardown."""
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        # If session is already gone (e.g. reaped), we just return success
        return {"status": "success", "detail": "Session not found or already terminated."}
    
    # Trigger background teardown
    background_tasks.add_task(teardown_environment_logic, session.environment_id, session_token)
    
    return {"status": "success", "detail": "Teardown initiated."}

@app.post("/lab/admin/reset/{env_id}", dependencies=[Depends(verify_api_key)])
async def admin_reset_environment(env_id: str):
    """Reset a faulted or stuck environment back to 'available'. Admin use only.

    Safe to call on 'faulted' or 'available' environments. Rejected with 409
    if the environment is actively provisioning or in use (which would orphan
    the running VM — use teardown instead).
    """
    previous = _reset_environment(env_id)
    logger.info(f"Admin reset: env '{env_id}' from '{previous}' to 'available'")
    return {"id": env_id, "previous_status": previous, "status": "available"}

@app.post("/lab/admin/reset-all-faulted", dependencies=[Depends(verify_api_key)])
async def admin_reset_all_faulted():
    """Reset all faulted environments to 'available' in a single call. Admin use only."""
    reset_ids = _reset_all_faulted()
    logger.info(f"Admin reset-all-faulted: reset {len(reset_ids)} environment(s): {reset_ids}")
    return {"reset": reset_ids, "count": len(reset_ids)}

@app.post("/lab/verify/{session_token}", dependencies=[Depends(verify_api_key)])
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

@app.post("/evaluate", dependencies=[Depends(verify_api_key)])
@app.post("/lab/evaluate", dependencies=[Depends(verify_api_key)])
async def evaluate_proxy(req: EvaluateRequest):
    # Determine which API key to use based on the model
    model = req.model or "claude-3-5-sonnet-20241022"
    api_key = settings.anthropic_api_key
    
    if not api_key:
        raise HTTPException(status_code=500, detail="AI Provider API Key not configured on server.")

    result = await perform_evaluation(
        api_key=api_key,
        model=model,
        scenario=req.scenario,
        artifact_content=req.artifactContent,
        response_text=req.responseText,
        coach_mode=req.coachMode,
        coach_round=req.coachRound,
        coach_history=req.coachHistory,
        compact_rubric=req.compactRubric
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
