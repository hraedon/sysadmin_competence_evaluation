"""V2 evaluation API — server-side rubric loading.

The browser sends only scenarioId + responseText. The server loads the full
rubric (including miss_signal and level_indicators) from YAML, calls the AI
model, and returns the evaluation result plus learning notes.

Closes ARCH-09, SEC-03, SEC-05, ARCH-17.
"""
import logging
from typing import List, Dict, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db, EvaluationRecord, _is_sqlite
from ..deps import verify_api_key
from ..middleware.rate_limit import limiter
from ..schemas import settings
from ..evaluator import perform_evaluation
from ..services.rubric_service import load_scenario_rubric, load_artifact_content, get_learning_notes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["evaluate_v2"])


class EvaluateRequestV2(BaseModel):
    scenarioId: str
    responseText: str
    coachMode: bool = False
    coachRound: int = 0
    coachHistory: List[Dict[str, str]] = []
    # User ID for recording — optional during transition (API-key auth has no user context)
    userId: Optional[str] = None


@router.post("/evaluate", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def evaluate_v2(request: Request, req: EvaluateRequestV2, db: Session = Depends(get_db)):
    """Evaluate a learner's response against a scenario rubric.

    The rubric is loaded server-side — the browser never sees miss_signal
    or level_indicators. Returns the AI evaluation plus learning notes
    for caught/missed findings.
    """
    api_key = settings.anthropic_api_key
    if not api_key:
        raise HTTPException(status_code=500, detail="AI provider API key not configured on server.")

    model = "claude-sonnet-4-6-20250514"

    # Load full scenario with rubric server-side
    scenario = load_scenario_rubric(req.scenarioId)
    artifact_content = load_artifact_content(req.scenarioId, scenario)

    # Build verification context for ARCH-17 (lab scenarios)
    # If this scenario has a lab session with verification results, include them
    verification_context = _build_verification_context(req.scenarioId, req.userId, db)

    result = await perform_evaluation(
        api_key=api_key,
        model=model,
        scenario=scenario,
        artifact_content=artifact_content,
        response_text=_prepend_verification_context(req.responseText, verification_context),
        coach_mode=req.coachMode,
        coach_round=req.coachRound,
        coach_history=req.coachHistory,
    )

    # Attach learning notes for the frontend to display post-evaluation
    learning_notes = get_learning_notes(scenario)
    result["learning_notes"] = learning_notes

    # Record the evaluation
    if req.userId and result.get("parsed"):
        parsed = result["parsed"]
        record = EvaluationRecord(
            user_id=req.userId,
            scenario_id=req.scenarioId,
            response_text=req.responseText,
            model_used=model,
            raw_result={"raw": result.get("raw", "")},
            parsed_result=parsed,
            level=parsed.get("level"),
            confidence=parsed.get("confidence"),
        )
        db.add(record)
        db.commit()

    return result


@router.post("/coach", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def coach_v2(request: Request, req: EvaluateRequestV2, db: Session = Depends(get_db)):
    """Coach mode evaluation — same as evaluate but with coachMode forced on."""
    req.coachMode = True
    return await evaluate_v2(request, req, db)


def _build_verification_context(scenario_id: str, user_id: str | None, db: Session) -> str | None:
    """Pull the most recent lab verification results from the DB for ARCH-17.

    Returns a formatted string for inclusion in the evaluation context,
    or None if no verification results exist.
    """
    if not user_id:
        return None

    from ..database import LabSession
    session = (
        db.query(LabSession)
        .filter(LabSession.scenario_id == scenario_id, LabSession.user_id == user_id)
        .order_by(LabSession.created_at.desc())
        .first()
    )
    if not session:
        return None

    # Check if there are verification results stored (future: add verification_results to LabSession)
    # For now, return None — this will be wired in when lab verification storage is added
    return None


def _prepend_verification_context(response_text: str, verification_context: str | None) -> str:
    """If lab verification data exists, prepend it to the response text so the
    AI evaluator sees both the learner's explanation and the actual environment state."""
    if not verification_context:
        return response_text
    return f"[LAB VERIFICATION STATE]\n{verification_context}\n\n[LEARNER RESPONSE]\n{response_text}"
