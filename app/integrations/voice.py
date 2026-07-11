from dataclasses import dataclass
from html import escape

import httpx

from app.core.config import Settings
from app.integrations.exceptions import IntegrationNotConfigured


@dataclass(frozen=True)
class AudioResult:
    content: bytes
    content_type: str


class ElevenLabsClient:
    def __init__(self, *, settings: Settings):
        self.settings = settings

    async def synthesize(self, *, text: str, voice_id: str | None = None) -> AudioResult:
        if not self.settings.elevenlabs_api_key:
            raise IntegrationNotConfigured("ELEVENLABS_API_KEY is required for synthesis.")
        selected_voice_id = voice_id or self.settings.elevenlabs_voice_id
        if not selected_voice_id:
            raise IntegrationNotConfigured("ELEVENLABS_VOICE_ID is required for synthesis.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}"
        headers = {
            "xi-api-key": self.settings.elevenlabs_api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        return AudioResult(content=response.content, content_type="audio/mpeg")


class TwilioTwiML:
    @staticmethod
    def gather_prompt(prompt: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            '<Gather input="speech" speechTimeout="auto" method="POST">'
            f"<Say>{escape(prompt)}</Say>"
            "</Gather>"
            f"<Say>{escape('I did not hear anything. Please call again when ready.')}</Say>"
            "</Response>"
        )

    @staticmethod
    def say(text: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"<Say>{escape(text)}</Say>"
            "</Response>"
        )
