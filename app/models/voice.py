from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VoiceSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "voice_sessions"

    provider: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    call_sid: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    phone_from: Mapped[str | None] = mapped_column(String(80))
    phone_to: Mapped[str | None] = mapped_column(String(80))
    transcript: Mapped[str | None] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False, default="started")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
