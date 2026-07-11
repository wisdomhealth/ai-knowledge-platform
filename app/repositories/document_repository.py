import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.models.integration import ScrapedPage, SheetSyncJob


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self,
        *,
        source: str,
        title: str,
        owner_id: uuid.UUID | None = None,
        external_id: str | None = None,
        mime_type: str | None = None,
        url: str | None = None,
        checksum: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        document = Document(
            owner_id=owner_id,
            source=source,
            external_id=external_id,
            title=title,
            mime_type=mime_type,
            url=url,
            checksum=checksum,
            metadata_json=metadata or {},
            indexed_at=datetime.now(UTC),
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def add_chunk(
        self,
        *,
        document_id: uuid.UUID,
        chunk_index: int,
        content: str,
        token_count: int | None = None,
        embedding_id: str | None = None,
        embedding_model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentChunk:
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            token_count=token_count,
            embedding_id=embedding_id,
            embedding_model=embedding_model,
            metadata_json=metadata or {},
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def search_chunks(self, query: str, *, limit: int = 5) -> list[DocumentChunk]:
        statement: Select[tuple[DocumentChunk]] = (
            select(DocumentChunk)
            .where(DocumentChunk.content.ilike(f"%{query}%"))
            .order_by(DocumentChunk.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def record_scraped_page(
        self,
        *,
        url: str,
        title: str | None,
        text_content: str,
        status_code: int,
        metadata: dict[str, Any] | None = None,
    ) -> ScrapedPage:
        digest = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        page = ScrapedPage(
            url=url,
            title=title,
            text_content=text_content,
            status_code=status_code,
            content_hash=digest,
            metadata_json=metadata or {},
            scraped_at=datetime.now(UTC),
        )
        self.session.add(page)
        await self.session.flush()
        return page

    async def record_sheet_job(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        operation: str,
        status: str,
        rows_processed: int,
        metadata: dict[str, Any] | None = None,
    ) -> SheetSyncJob:
        job = SheetSyncJob(
            spreadsheet_id=spreadsheet_id,
            range_name=range_name,
            operation=operation,
            status=status,
            rows_processed=rows_processed,
            metadata_json=metadata or {},
        )
        self.session.add(job)
        await self.session.flush()
        return job
