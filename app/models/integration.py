from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SheetSyncJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sheet_sync_jobs"

    spreadsheet_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    range_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False, default="pending")
    rows_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )


class ScrapedPage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scraped_pages"

    url: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IntegrationCredential(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "integration_credentials"

    provider: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    account_id: Mapped[str | None] = mapped_column(String(255), index=True)
    secret_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
