import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentRun, ToolExecution
from app.models.conversation import Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        *,
        user_id: uuid.UUID | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title, metadata_json=metadata or {})
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def add_message(
        self,
        *,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        token_count: int | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            token_count=token_count,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_recent_messages(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int = 12,
    ) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def create_agent_run(
        self,
        *,
        agent_type: str,
        conversation_id: uuid.UUID | None = None,
        goal: str | None = None,
        input_json: dict[str, Any] | None = None,
    ) -> AgentRun:
        run = AgentRun(
            conversation_id=conversation_id,
            agent_type=agent_type,
            status="running",
            goal=goal,
            input_json=input_json or {},
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def complete_agent_run(
        self,
        run: AgentRun,
        *,
        status: str,
        output_json: dict[str, Any] | None = None,
        trace: list[dict[str, Any]] | None = None,
    ) -> AgentRun:
        run.status = status
        run.output_json = output_json or {}
        run.trace = trace or []
        run.completed_at = datetime.now(UTC)
        await self.session.flush()
        return run

    async def add_tool_execution(
        self,
        *,
        agent_run_id: uuid.UUID,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None = None,
        status: str = "completed",
        error: str | None = None,
    ) -> ToolExecution:
        now = datetime.now(UTC)
        execution = ToolExecution(
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result or {},
            status=status,
            error=error,
            started_at=now,
            completed_at=now,
        )
        self.session.add(execution)
        await self.session.flush()
        return execution
