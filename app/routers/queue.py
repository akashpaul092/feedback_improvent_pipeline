"""Queue processing - process pending conversations from Redis."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Evaluation
from app.queue import dequeue_conversation, queue_length
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/queue", tags=["queue"])
eval_service = EvaluationService()


@router.get("/status")
def queue_status():
    """Get number of pending conversations in queue."""
    return {"pending": queue_length()}


@router.post("/process")
def process_one(db: Session = Depends(get_db)):
    """Process one conversation from the queue."""
    payload = dequeue_conversation()
    if not payload:
        return {"status": "empty", "message": "No pending conversations"}

    data = payload.get("data", payload)
    conv_id = data.get("conversation_id")

    # Run evaluation
    result = eval_service.evaluate(data)

    # Store evaluation
    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conv_id
    ).first()
    if conv:
        eval_model = Evaluation(
            evaluation_id=result["evaluation_id"],
            conversation_id=conv_id,
            scores=result["scores"],
            tool_evaluation=result["tool_evaluation"],
            issues_detected=result["issues_detected"],
            improvement_suggestions=result["improvement_suggestions"],
        )
        db.add(eval_model)
        conv.processed = True
        db.commit()

    return {"status": "processed", "evaluation_id": result["evaluation_id"]}
