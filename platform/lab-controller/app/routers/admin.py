import yaml
import json
import re
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db, LabEnvironment, LabSession
from ..deps import verify_api_key, orchestrator
from ..utils import resolve_scenario_path
from ..schemas import VerificationResult
from ..services.lab_service import reset_environment, reset_all_faulted

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lab", tags=["admin"])

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    envs = db.query(LabEnvironment).all()
    faulted = [e.id for e in envs if e.status == "faulted"]
    available = sum(1 for e in envs if e.status == "available")
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

@router.post("/admin/reset/{env_id}", dependencies=[Depends(verify_api_key)])
async def admin_reset_environment(env_id: str):
    previous = reset_environment(env_id)
    logger.info(f"Admin reset: env '{env_id}' from '{previous}' to 'available'")
    return {"id": env_id, "previous_status": previous, "status": "available"}

@router.post("/admin/reset-all-faulted", dependencies=[Depends(verify_api_key)])
async def admin_reset_all_faulted_endpoint():
    reset_ids = reset_all_faulted()
    logger.info(f"Admin reset-all-faulted: reset {len(reset_ids)} environment(s): {reset_ids}")
    return {"reset": reset_ids, "count": len(reset_ids)}

@router.post("/verify/{session_token}", dependencies=[Depends(verify_api_key)])
async def verify_lab(session_token: str, db: Session = Depends(get_db)):
    session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found.")
    
    scenario_path = resolve_scenario_path(session.scenario_id)
    with open(scenario_path, 'r') as f:
        scenario = yaml.safe_load(f)
    
    config = scenario.get('presentation', {}).get('modes', {}).get('E', {}).get('config', {})
    verification_steps = config.get('verification', [])
    
    results = []
    for step in verification_steps:
        target = step.get('target')
        script_path = scenario_path.parent / step.get('file')
        finding_id = step.get('finding_id')
        
        res = await orchestrator.run_script_in_guest(target, str(script_path))
        if res.success:
            # ARCH-16: Robust JSON extraction
            raw = res.output.strip()
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw) or re.search(r'(\{[\s\S]*\})', raw)
            json_str = json_match.group(1) if json_match else raw
            
            try:
                parsed = json.loads(json_str)
                results.append(VerificationResult(finding_id=finding_id, status=parsed.get('status', 'incomplete'), detail=parsed.get('detail', '')))
            except:
                results.append(VerificationResult(finding_id=finding_id, status="incomplete", detail=f"Verification script output could not be parsed: {raw[:100]}"))
        else:
            results.append(VerificationResult(finding_id=finding_id, status="incomplete", detail=f"Verification script failed: {res.error}"))
    return results
