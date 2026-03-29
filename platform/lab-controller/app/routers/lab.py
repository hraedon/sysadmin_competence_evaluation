import yaml
import uuid
import datetime
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from pathlib import Path

from ..database import get_db, LabEnvironment, LabSession, _is_sqlite
from ..schemas import ProvisionRequest, ProvisionResponse, settings
from ..deps import verify_api_key, verify_api_key_or_jwt, guac_client
from ..middleware.rate_limit import limiter
from ..utils import sanitize_scenario_id, resolve_scenario_path
from ..services.lab_service import run_provisioning_with_watchdog, teardown_environment_logic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lab", tags=["lab"])

@router.get("/status", dependencies=[Depends(verify_api_key)])
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

@router.post("/provision/{scenario_id}", response_model=ProvisionResponse, dependencies=[Depends(verify_api_key_or_jwt)])
@limiter.limit("5/minute")
async def provision_lab(
    request: Request,
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

    required_capabilities = mode_e.get('capabilities', [])

    # --- Atomic environment selection (ARCH-01 fix) ---
    # PostgreSQL: SELECT FOR UPDATE SKIP LOCKED prevents race conditions at replicas > 1.
    # SQLite: Falls back to optimistic update (safe at replicas=1).
    query = db.query(LabEnvironment).filter(LabEnvironment.status == "available")
    if not _is_sqlite:
        query = query.with_for_update(skip_locked=True)

    available_envs = query.all()

    selected_env = None
    for env in available_envs:
        env_caps = set(env.capabilities or [])
        if all(cap in env_caps for cap in required_capabilities):
            selected_env = env
            break

    if not selected_env:
        all_envs = db.query(LabEnvironment).all()
        if not all_envs:
            detail = "No lab environments configured."
        elif not available_envs:
            detail = f"No available environments. {len(all_envs)} environments exist but none are 'available'."
        else:
            detail = f"No available environment supports capabilities {required_capabilities}."
        raise HTTPException(status_code=503, detail=detail)

    if _is_sqlite:
        # SQLite fallback: optimistic update with status check
        affected = db.query(LabEnvironment).filter(
            LabEnvironment.id == selected_env.id,
            LabEnvironment.status == "available"
        ).update({"status": "provisioning"})
        if affected == 0:
            db.rollback()
            raise HTTPException(status_code=503, detail="Contention detected. Please retry.")
    else:
        # PostgreSQL: row is already locked by FOR UPDATE
        selected_env.status = "provisioning"

    db.commit()

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

    background_tasks.add_task(
        run_provisioning_with_watchdog,
        selected_env.id,
        scenario_path,
        mode_e,
        session_token
    )

    return ProvisionResponse(
        status="provisioning",
        session_token=session_token,
        environment_id=selected_env.id,
        expires_at=expires_at,
        instructions=mode_e.get('instructions', '')
    )

@router.get("/session/{session_token}", dependencies=[Depends(verify_api_key_or_jwt)])
async def get_session_status(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    env = db.query(LabEnvironment).filter(LabEnvironment.id == session.environment_id).first()
    
    if not guac_client.token:
        try: await guac_client._authenticate()
        except: pass

    guacamole_url = None
    if session.guac_connection_id:
        # SEC-07: Authenticate as session user (restricted) instead of admin
        if session.guac_session_username and session.guac_session_password:
            try:
                token = await guac_client.authenticate_session_user(
                    session.guac_session_username, session.guac_session_password
                )
                guacamole_url = guac_client._session_client_url(session.guac_connection_id, token)
            except Exception:
                logger.warning(f"SEC-07: Session user auth failed, falling back to admin token")
                guacamole_url = guac_client._client_url(session.guac_connection_id)
        else:
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

@router.post("/renew/{session_token}", dependencies=[Depends(verify_api_key_or_jwt)])
async def renew_session(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    now = datetime.datetime.utcnow()
    session.expires_at = min(now + datetime.timedelta(minutes=30), session.max_expires_at)
    db.commit()
    return {"expires_at": session.expires_at}

@router.post("/teardown/{session_token}", dependencies=[Depends(verify_api_key_or_jwt)])
async def teardown_lab(session_token: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        return {"status": "success", "detail": "Session not found or already terminated."}
    background_tasks.add_task(teardown_environment_logic, session.environment_id, session_token)
    return {"status": "success", "detail": "Teardown initiated."}
