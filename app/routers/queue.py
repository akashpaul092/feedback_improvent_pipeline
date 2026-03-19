"""Queue processing - process pending conversations from Redis."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Evaluation
from app.queue import dequeue_conversation, dequeue_conversations, queue_length
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/queue", tags=["queue"])
eval_service = EvaluationService()


@router.get("/status")
def queue_status():
    """Get number of pending conversations in queue."""
    return {"pending": queue_length()}


def _process_payload(payload: dict, db: Session) -> dict | None:
    """Process a single queue payload and store evaluation. Returns result or None."""
    data = payload.get("data", payload)
    conv_id = data.get("conversation_id")
    result = eval_service.evaluate(data)
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
    return {"evaluation_id": result["evaluation_id"], "conversation_id": conv_id}


@router.post("/process")
def process_queue(
    db: Session = Depends(get_db),
    batch_size: int = Query(1, ge=1, le=100, description="Number of conversations to process"),
):
    """Process one or more conversations from the queue."""
    if batch_size == 1:
        payload = dequeue_conversation()
        if not payload:
            return {"status": "empty", "message": "No pending conversations"}
        result = _process_payload(payload, db)
        db.commit()
        return {"status": "processed", "evaluation_id": result["evaluation_id"]}

    payloads = dequeue_conversations(batch_size)
    if not payloads:
        return {"status": "empty", "message": "No pending conversations", "processed": 0}

    results = []
    for payload in payloads:
        r = _process_payload(payload, db)
        if r:
            results.append(r)
    db.commit()
    return {"status": "processed", "processed": len(results), "evaluations": results}
