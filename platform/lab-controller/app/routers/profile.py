"""Profile API — server-side profile storage. Closes EVAL-03."""
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db, EvaluationRecord, User
from ..deps import get_current_user
from ..services.profile_service import get_profile, save_result, import_profile, export_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


class SaveResultRequest(BaseModel):
    scenario_id: str
    domain: int | str
    domain_name: str = ""
    level: int | None = None
    confidence: str | None = None
    gap: str | None = None
    almost_caught: list[str] = []


class ImportProfileRequest(BaseModel):
    profile: dict[str, Any]


@router.get("")
async def get_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_profile(db, user.id)


@router.post("/result")
async def save_evaluation_result(
    req: SaveResultRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return save_result(db, user.id, req.scenario_id, req.model_dump())


@router.post("/import")
async def import_user_profile(
    req: ImportProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import a profile from localStorage (one-time migration on first login)."""
    return import_profile(db, user.id, req.profile)


@router.get("/export")
async def export_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return export_profile(db, user.id)


@router.get("/history")
async def evaluation_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's evaluation records (most recent first)."""
    records = (
        db.query(EvaluationRecord)
        .filter(EvaluationRecord.user_id == user.id)
        .order_by(EvaluationRecord.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "scenario_id": r.scenario_id,
            "level": r.level,
            "confidence": r.confidence,
            "model_used": r.model_used,
            "created_at": r.created_at,
        }
        for r in records
    ]
