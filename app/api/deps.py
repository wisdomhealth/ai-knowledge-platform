from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.integrations.google_sheets import GoogleSheetsClient
from app.integrations.openai_client import OpenAIClient
from app.integrations.voice import ElevenLabsClient
from app.integrations.web_scraper import WebScraperClient
from app.rag.service import RagService
from app.rag.vector_store import ChromaVectorStore
from app.services.agent_service import AgentService
from app.services.google_sheets_service import GoogleSheetsService
from app.services.voice_service import VoiceService
from app.services.web_scraper_service import WebScraperService


def get_app_settings() -> Settings:
    return get_settings()


async def get_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


def get_google_sheets_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> GoogleSheetsService:
    return GoogleSheetsService(
        session=session,
        client=GoogleSheetsClient(settings=settings),
    )


def get_web_scraper_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> WebScraperService:
    return WebScraperService(
        session=session,
        client=WebScraperClient(settings=settings),
    )


def get_openai_client(settings: Annotated[Settings, Depends(get_app_settings)]) -> OpenAIClient:
    return OpenAIClient(settings=settings)


def get_rag_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> RagService:
    return RagService(
        session=session,
        openai_client=OpenAIClient(settings=settings),
        vector_store=ChromaVectorStore(settings=settings),
    )


def get_agent_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AgentService:
    openai_client = OpenAIClient(settings=settings)
    rag_service = RagService(
        session=session,
        openai_client=openai_client,
        vector_store=ChromaVectorStore(settings=settings),
    )
    return AgentService(
        session=session,
        openai_client=openai_client,
        rag_service=rag_service,
        google_sheets_service=GoogleSheetsService(
            session=session,
            client=GoogleSheetsClient(settings=settings),
        ),
        web_scraper_service=WebScraperService(
            session=session,
            client=WebScraperClient(settings=settings),
        ),
    )


def get_voice_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> VoiceService:
    return VoiceService(
        session=session,
        elevenlabs_client=ElevenLabsClient(settings=settings),
    )
