from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.voice import AudioResult, ElevenLabsClient, TwilioTwiML
from app.repositories.voice_repository import VoiceRepository


class VoiceService:
    def __init__(self, *, session: AsyncSession, elevenlabs_client: ElevenLabsClient):
        self.session = session
        self.elevenlabs_client = elevenlabs_client
        self.repository = VoiceRepository(session)

    async def record_twilio_turn(
        self,
        *,
        call_sid: str,
        phone_from: str | None,
        phone_to: str | None,
        transcript: str | None,
    ):
        session = await self.repository.upsert_twilio_session(
            call_sid=call_sid,
            phone_from=phone_from,
            phone_to=phone_to,
            transcript=transcript,
            status="in_progress",
        )
        await self.session.commit()
        return session

    def prompt_twilio(self) -> str:
        return TwilioTwiML.gather_prompt("Tell me what you want to know about your documents.")

    def answer_twilio(self, answer: str) -> str:
        return TwilioTwiML.say(answer[:1500])

    async def synthesize(self, *, text: str, voice_id: str | None = None) -> AudioResult:
        return await self.elevenlabs_client.synthesize(text=text, voice_id=voice_id)
