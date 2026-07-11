from typing import Any

from app.core.config import Settings
from app.integrations.exceptions import IntegrationNotConfigured

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - dependency is declared for runtime installs
    AsyncOpenAI = None


class OpenAIClient:
    def __init__(self, *, settings: Settings):
        self.settings = settings
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if AsyncOpenAI is None:
            raise IntegrationNotConfigured("OpenAI dependency is not installed.")
        if not self.settings.openai_api_key:
            raise IntegrationNotConfigured("OPENAI_API_KEY is required for OpenAI calls.")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    async def chat(self, *, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.settings.openai_chat_model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        return content or ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
