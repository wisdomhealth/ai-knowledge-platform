import asyncio
import logging
import time

from langchain_core.messages import convert_to_messages
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.exceptions import IntegrationNotConfigured

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, *, settings: Settings):
        self.settings = settings

    def _require_key(self) -> str:
        if not self.settings.openai_api_key:
            raise IntegrationNotConfigured("OPENAI_API_KEY is required for OpenAI calls.")
        return self.settings.openai_api_key

    async def chat(self, *, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        key = self._require_key()
        model = ChatOpenAI(
            api_key=SecretStr(key),
            model=self.settings.openai_chat_model,
            temperature=temperature,
            timeout=self.settings.call_timeout_seconds,
            max_retries=0,
        )
        started = time.monotonic()
        try:
            async with asyncio.timeout(self.settings.call_timeout_seconds):
                response = await model.ainvoke(convert_to_messages(messages))
        finally:
            logger.info(
                "model_call model=%s duration_ms=%.1f",
                self.settings.openai_chat_model,
                (time.monotonic() - started) * 1000,
            )
        content = response.content
        if isinstance(content, str):
            return content
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        key = self._require_key()
        if not texts:
            return []
        # Explicit vectors are handed to LlamaIndex/Chroma; neither embeds again.
        async with AsyncOpenAI(
            api_key=key, timeout=self.settings.call_timeout_seconds, max_retries=0
        ) as client:
            vectors: list[list[float]] = []
            for offset in range(0, len(texts), 128):
                batch = texts[offset : offset + 128]
                async with asyncio.timeout(self.settings.call_timeout_seconds):
                    response = await client.embeddings.create(
                        model=self.settings.openai_embedding_model, input=batch
                    )
                vectors.extend(
                    item.embedding for item in sorted(response.data, key=lambda x: x.index)
                )
            return vectors
