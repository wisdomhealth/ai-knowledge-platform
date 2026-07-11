import uuid

from pydantic import BaseModel, Field

from app.schemas.agents import ConversationResponse, RagSourceSchema


class DriveSyncRequest(BaseModel):
    folder_id: str | None = None
    max_files: int = Field(default=25, ge=1, le=100)


class DriveSyncResponse(BaseModel):
    documents_indexed: int
    chunks_indexed: int
    document_ids: list[uuid.UUID]


class DriveSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class DriveSearchResponse(BaseModel):
    results: list[RagSourceSchema]


class DriveAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: uuid.UUID | None = None
    rag_limit: int = Field(default=5, ge=1, le=20)


class DriveAskResponse(ConversationResponse):
    pass
