"""Evaluation API - run evals, query results, suggestions, calibration."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Evaluation
from app.schemas import EvaluationResponse, EvaluationQuery, PaginatedEvaluations
from app.services.evaluation_service import EvaluationService
from app.services.calibration_service import CalibrationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

eval_service = EvaluationService()
calibration_service = CalibrationService()


def _apply_calibration(scores: dict) -> dict:
    """Apply self-healing calibration to scores."""
    if not scores:
        return scores
    return {
        **scores,
        "response_quality": round(calibration_service.apply("response_quality", scores.get("response_quality", 0.5)), 2),
        "tool_accuracy": round(calibration_service.apply("tool_accuracy", scores.get("tool_accuracy", 0.5)), 2),
        "coherence": round(calibration_service.apply("coherence", scores.get("coherence", 0.5)), 2),
        "overall": round(
            calibration_service.apply("response_quality", scores.get("response_quality", 0.5)) * 0.4
            + calibration_service.apply("tool_accuracy", scores.get("tool_accuracy", 0.5)) * 0.35
            + calibration_service.apply("coherence", scores.get("coherence", 0.5)) * 0.25,
            2,
        ),
    }


def _eval_to_response(e: Evaluation) -> dict:
    """Convert DB model to API response (calibrated scores)."""
    scores = _apply_calibration(e.scores or {})
    return {
        "evaluation_id": e.evaluation_id,
        "conversation_id": e.conversation_id,
        "scores": scores,
        "tool_evaluation": e.tool_evaluation or {},
        "issues_detected": e.issues_detected or [],
        "improvement_suggestions": e.improvement_suggestions or [],
    }


@router.post("/run/{conversation_id}")
def run_evaluation(conversation_id: str, db: Session = Depends(get_db)):
    """Run evaluation for a conversation (sync)."""
    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    data = {
        "conversation_id": conv.conversation_id,
        "agent_version": conv.agent_version,
        "turns": conv.turns,
        "feedback": conv.feedback or {},
        "metadata": conv.metadata_ or {},
    }
    result = eval_service.evaluate(data)

    # Store evaluation (raw scores for calibration)
    eval_model = Evaluation(
        evaluation_id=result["evaluation_id"],
        conversation_id=conv.conversation_id,
        scores=result["scores"],
        tool_evaluation=result["tool_evaluation"],
        issues_detected=result["issues_detected"],
        improvement_suggestions=result["improvement_suggestions"],
    )
    db.add(eval_model)
    conv.processed = True
    db.commit()

    # Return calibrated scores for display
    result["scores"] = _apply_calibration(result["scores"])
    return result


@router.get("", response_model=PaginatedEvaluations)
def list_evaluations(
    conversation_id: str | None = None,
    agent_version: str | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Query evaluations with optional filters."""
    q = db.query(Evaluation)
    if conversation_id:
        q = q.filter(Evaluation.conversation_id == conversation_id)
    if agent_version:
        q = q.join(Conversation, Evaluation.conversation_id == Conversation.conversation_id).filter(
            Conversation.agent_version == agent_version
        )

    total = q.count()
    evals = q.order_by(Evaluation.created_at.desc()).limit(limit).all()

    return PaginatedEvaluations(
        total=total,
        evaluations=[_eval_to_response(e) for e in evals],
    )


@router.get("/suggestions")
def get_improvement_suggestions(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """Get aggregated improvement suggestions."""
    evals = db.query(Evaluation).order_by(Evaluation.created_at.desc()).limit(limit * 5).all()
    evals = [e for e in evals if e.improvement_suggestions]

    suggestions = []
    seen = set()
    for e in evals:
        for s in (e.improvement_suggestions or []):
            key = (s.get("type"), s.get("suggestion", "")[:80])
            if key not in seen:
                seen.add(key)
                suggestions.append(s)
                if len(suggestions) >= limit:
                    break
        if len(suggestions) >= limit:
            break

    return {"suggestions": suggestions}


@router.get("/calibration")
def get_calibration():
    """Get current evaluator calibration (self-healing state)."""
    return {"calibration": calibration_service.get_calibration()}


@router.post("/calibrate")
def run_calibration(db: Session = Depends(get_db)):
    """
    Run calibration: compare evaluator scores with human annotations,
    update calibration params when they diverge. Detects blind spots.
    """
    convs = db.query(Conversation).all()
    evals = db.query(Evaluation).all()

    conv_data = [
        {
            "conversation_id": c.conversation_id,
            "feedback": c.feedback or {},
        }
        for c in convs
    ]
    eval_data = [
        {
            "conversation_id": e.conversation_id,
            "scores": e.scores or {},
            "tool_evaluation": e.tool_evaluation or {},
        }
        for e in evals
    ]

    result = calibration_service.run_calibration(conv_data, eval_data)
    return result
