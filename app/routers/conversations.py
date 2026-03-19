"""Conversation ingestion API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation
from app.schemas import ConversationCreate, ConversationResponse, BatchIngestResponse
from app.queue import enqueue_conversation
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/ingest", response_model=ConversationResponse)
def ingest_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    """Ingest a conversation - stores in DB and queues for evaluation."""
    # Check if already exists
    existing = db.query(Conversation).filter(
        Conversation.conversation_id == data.conversation_id
    ).first()
    if existing:
        return ConversationResponse(
            conversation_id=data.conversation_id,
            agent_version=data.agent_version,
            status="already_exists",
        )

    # Store in DB
    conv = Conversation(
        conversation_id=data.conversation_id,
        agent_version=data.agent_version,
        turns=data.turns,
        feedback=data.feedback or {},
        metadata_=data.metadata or {},
    )
    db.add(conv)
    db.commit()

    # Queue for evaluation
    payload = {
        "conversation_id": data.conversation_id,
        "agent_version": data.agent_version,
        "turns": data.turns,
        "feedback": data.feedback or {},
        "metadata": data.metadata or {},
    }
    enqueue_conversation(payload)

    return ConversationResponse(
        conversation_id=data.conversation_id,
        agent_version=data.agent_version,
        status="queued",
    )


@router.post("/ingest/batch", response_model=BatchIngestResponse)
def ingest_conversations_batch(
    items: list[ConversationCreate], db: Session = Depends(get_db)
):
    """Ingest multiple conversations - stores in DB and queues each for evaluation."""
    results = []
    for data in items:
        existing = db.query(Conversation).filter(
            Conversation.conversation_id == data.conversation_id
        ).first()
        if existing:
            results.append(
                ConversationResponse(
                    conversation_id=data.conversation_id,
                    agent_version=data.agent_version,
                    status="already_exists",
                )
            )
            continue

        conv = Conversation(
            conversation_id=data.conversation_id,
            agent_version=data.agent_version,
            turns=data.turns,
            feedback=data.feedback or {},
            metadata_=data.metadata or {},
        )
        db.add(conv)
        payload = {
            "conversation_id": data.conversation_id,
            "agent_version": data.agent_version,
            "turns": data.turns,
            "feedback": data.feedback or {},
            "metadata": data.metadata or {},
        }
        enqueue_conversation(payload)
        results.append(
            ConversationResponse(
                conversation_id=data.conversation_id,
                agent_version=data.agent_version,
                status="queued",
            )
        )
    db.commit()
    return BatchIngestResponse(ingested=len(results), results=results)
