"""Feedback integration - annotations, disagreement handling."""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.models import Conversation

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _compute_agreement(annotations: list) -> dict:
    """Handle annotator disagreement - compute agreement metrics."""
    if not annotations or len(annotations) < 2:
        return {"agreement": "single_annotator", "needs_review": False}

    labels = [a.get("label") for a in annotations if a.get("label")]
    unique = set(labels)
    if len(unique) == 1:
        return {"agreement": "full", "needs_review": False}
    return {"agreement": "disagreement", "needs_review": True, "labels": list(unique)}


@router.post("/annotations/{conversation_id}")
def add_annotations(
    conversation_id: str,
    annotations: list[dict] = Body(...),
    db: Session = Depends(get_db),
):
    """Add human annotations to a conversation. Handles disagreement."""
    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()
    if not conv:
        return {"error": "Conversation not found"}

    existing = list(conv.feedback.get("annotations", []) or [])
    existing.extend(annotations)
    conv.feedback = {**(conv.feedback or {}), "annotations": existing}
    flag_modified(conv, "feedback")  # Force SQLAlchemy to detect JSON column change
    db.commit()

    agreement = _compute_agreement(existing)
    return {
        "conversation_id": conversation_id,
        "annotations_count": len(existing),
        "agreement": agreement,
    }
