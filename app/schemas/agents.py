import uuid
from typing import Any

from pydantic import BaseModel, Field


class RagSourceSchema(BaseModel):
    document_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    title: str | None
    content: str
    score: float | None


class ConversationRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    use_rag: bool = True
    rag_limit: int = Field(default=5, ge=1, le=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    conversation_id: uuid.UUID
    run_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    answer: str
    sources: list[RagSourceSchema]


class WorkflowStep(BaseModel):
    tool_name: str = Field(..., examples=["rag.search", "web.scrape", "sheets.read"])
    arguments: dict[str, Any] = Field(default_factory=dict)


class WorkflowRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    conversation_id: uuid.UUID | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)


class WorkflowResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    results: list[dict[str, Any]]
    trace: list[dict[str, Any]]
