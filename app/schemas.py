"""Pydantic schemas for API request/response."""
from typing import Any, Optional
from pydantic import BaseModel, Field


# --- Conversation ---
class Turn(BaseModel):
    turn_id: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[list] = None
    timestamp: Optional[str] = None


class Annotation(BaseModel):
    type: str
    label: str
    annotator_id: str


class Feedback(BaseModel):
    user_rating: Optional[int] = None
    ops_review: Optional[dict] = None
    annotations: Optional[list[Annotation]] = None


class ConversationCreate(BaseModel):
    conversation_id: str
    agent_version: str
    turns: list[dict]
    feedback: Optional[dict] = None
    metadata: Optional[dict] = None


class ConversationResponse(BaseModel):
    conversation_id: str
    agent_version: str
    status: str = "queued"


class BatchIngestResponse(BaseModel):
    ingested: int
    results: list[ConversationResponse]


# --- Evaluation ---
class IssueDetected(BaseModel):
    type: str
    severity: str
    description: str


class EvaluationSuggestion(BaseModel):
    type: str  # prompt, tool
    suggestion: str
    rationale: str
    confidence: float


class EvaluationResponse(BaseModel):
    evaluation_id: str
    conversation_id: str
    scores: dict[str, float]
    tool_evaluation: dict[str, Any]
    issues_detected: list[IssueDetected]
    improvement_suggestions: list[EvaluationSuggestion]


# --- API responses ---
class EvaluationQuery(BaseModel):
    conversation_id: Optional[str] = None
    agent_version: Optional[str] = None
    limit: int = 50


class PaginatedEvaluations(BaseModel):
    total: int
    evaluations: list[EvaluationResponse]
