"""SQLAlchemy database models."""
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Conversation(Base):
    """Stored conversation with turns and feedback."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(100), unique=True, index=True, nullable=False)
    agent_version = Column(String(50), index=True, nullable=False)
    turns = Column(JSON, nullable=False)  # List of turn objects
    feedback = Column(JSON, default=dict)  # user_rating, ops_review, annotations
    metadata_ = Column("metadata", JSON, default=dict)  # total_latency_ms, mission_completed
    created_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)

    evaluations = relationship("Evaluation", back_populates="conversation")


class Evaluation(Base):
    """Evaluation result for a conversation."""

    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(String(100), unique=True, index=True, nullable=False)
    conversation_id = Column(String(100), ForeignKey("conversations.conversation_id"), nullable=False)
    scores = Column(JSON, nullable=False)  # overall, response_quality, tool_accuracy, coherence
    tool_evaluation = Column(JSON, default=dict)
    issues_detected = Column(JSON, default=list)
    improvement_suggestions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="evaluations")


class ImprovementSuggestion(Base):
    """Aggregated improvement suggestions for meta-learning."""

    __tablename__ = "improvement_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    suggestion_type = Column(String(50), index=True)  # prompt, tool
    suggestion = Column(Text, nullable=False)
    rationale = Column(Text)
    confidence = Column(Float, default=0.0)
    occurrence_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
