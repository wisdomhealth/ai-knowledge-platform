from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice import VoiceSession


class VoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_twilio_session(
        self,
        *,
        call_sid: str,
        phone_from: str | None,
        phone_to: str | None,
        transcript: str | None = None,
        status: str = "in_progress",
        metadata: dict[str, Any] | None = None,
    ) -> VoiceSession:
        existing = await self.session.scalar(
            select(VoiceSession).where(VoiceSession.call_sid == call_sid)
        )
        if existing is None:
            session = VoiceSession(provider="twilio", call_sid=call_sid)
            self.session.add(session)
        else:
            session = existing

        session.phone_from = phone_from
        session.phone_to = phone_to
        session.transcript = transcript
        session.status = status
        session.metadata_json = metadata or {}
        await self.session.flush()
        return session
