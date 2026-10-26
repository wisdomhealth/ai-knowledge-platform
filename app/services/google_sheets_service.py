from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google_sheets import GoogleSheetsClient
from app.repositories.document_repository import DocumentRepository
from app.schemas.google_sheets import (
    SheetAppendRequest,
    SheetAppendResponse,
    SheetReadRequest,
    SheetReadResponse,
)


class GoogleSheetsService:
    def __init__(self, *, session: AsyncSession, client: GoogleSheetsClient):
        self.session = session
        self.client = client
        self.documents = DocumentRepository(session)

    async def read_range(self, payload: SheetReadRequest) -> SheetReadResponse:
        values = await self.client.read_range(
            spreadsheet_id=payload.spreadsheet_id,
            range_name=payload.range_name,
        )
        job = await self.documents.record_sheet_job(
            spreadsheet_id=payload.spreadsheet_id,
            range_name=payload.range_name,
            operation="read",
            status="completed",
            rows_processed=len(values),
        )
        await self.session.commit()
        return SheetReadResponse(
            spreadsheet_id=payload.spreadsheet_id,
            range_name=payload.range_name,
            values=values,
            rows=len(values),
            job_id=job.id,
        )

    async def append_rows(
        self,
        payload: SheetAppendRequest,
        *,
        on_confirmed: Callable[[dict[str, Any]], None] | None = None,
    ) -> SheetAppendResponse:
        result = await self.client.append_rows(
            spreadsheet_id=payload.spreadsheet_id,
            range_name=payload.range_name,
            values=payload.values,
        )
        # Capture remote confirmation synchronously before any database await.
        if on_confirmed is not None:
            on_confirmed({"raw_result": result, "audit_status": "not_completed"})
        updates = result.get("updates", {})
        rows = int(updates.get("updatedRows") or len(payload.values))
        job = await self.documents.record_sheet_job(
            spreadsheet_id=payload.spreadsheet_id,
            range_name=payload.range_name,
            operation="append",
            status="completed",
            rows_processed=rows,
            metadata={"updates": updates},
        )
        await self.session.commit()
        return SheetAppendResponse(
            spreadsheet_id=payload.spreadsheet_id,
            range_name=payload.range_name,
            updated_range=updates.get("updatedRange"),
            updated_rows=rows,
            raw_result=result,
            job_id=job.id,
        )
