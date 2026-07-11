from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False, default="pending")
    goal: Mapped[str | None] = mapped_column(Text)
    input_json: Mapped[dict[str, Any]] = mapped_column("input", JSONB, default=dict, nullable=False)
    output_json: Mapped[dict[str, Any]] = mapped_column("output", JSONB, default=dict, nullable=False)
    trace: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tool_executions = relationship(
        "ToolExecution",
        back_populates="agent_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ToolExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tool_executions"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent_run = relationship("AgentRun", back_populates="tool_executions")
