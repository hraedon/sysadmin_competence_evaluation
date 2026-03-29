from fastapi import APIRouter, HTTPException, Depends
from ..schemas import EvaluateRequest, settings
from ..deps import verify_api_key_or_jwt
from ..evaluator import perform_evaluation

router = APIRouter(tags=["evaluate"])

@router.post("/evaluate", dependencies=[Depends(verify_api_key_or_jwt)])
@router.post("/lab/evaluate", dependencies=[Depends(verify_api_key_or_jwt)])
async def evaluate_proxy(req: EvaluateRequest):
    model = req.model or "claude-sonnet-4-6-20250514"
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
