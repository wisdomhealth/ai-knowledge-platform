import uuid

from pydantic import BaseModel, Field


class VoiceSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice_id: str | None = None


class VoiceSessionResponse(BaseModel):
    session_id: uuid.UUID
    call_sid: str | None
    status: str
