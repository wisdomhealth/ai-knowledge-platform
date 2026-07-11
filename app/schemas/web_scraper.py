import uuid

from pydantic import AnyHttpUrl, BaseModel, Field


class ScrapeRequest(BaseModel):
    url: AnyHttpUrl


class ScrapeResponse(BaseModel):
    page_id: uuid.UUID
    url: str
    title: str | None
    text: str = Field(..., max_length=20000)
    status_code: int
    content_hash: str
    content_type: str | None
