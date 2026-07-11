import uuid
from typing import Any

from pydantic import BaseModel, Field


class SheetReadRequest(BaseModel):
    spreadsheet_id: str = Field(..., min_length=1)
    range_name: str = Field(..., min_length=1, examples=["Sheet1!A1:D20"])


class SheetReadResponse(BaseModel):
    spreadsheet_id: str
    range_name: str
    values: list[list[Any]]
    rows: int
    job_id: uuid.UUID


class SheetAppendRequest(BaseModel):
    spreadsheet_id: str = Field(..., min_length=1)
    range_name: str = Field(..., min_length=1, examples=["Sheet1!A:D"])
    values: list[list[Any]] = Field(..., min_length=1)


class SheetAppendResponse(BaseModel):
    spreadsheet_id: str
    range_name: str
    updated_range: str | None
    updated_rows: int
    raw_result: dict[str, Any]
    job_id: uuid.UUID
