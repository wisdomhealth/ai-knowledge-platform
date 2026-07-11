from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.integrations.google_sheets import GoogleSheetsClient
from app.integrations.web_scraper import WebScraperClient
from app.services.google_sheets_service import GoogleSheetsService
from app.services.web_scraper_service import WebScraperService


def get_app_settings() -> Settings:
    return get_settings()


async def get_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


def get_google_sheets_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> GoogleSheetsService:
    return GoogleSheetsService(
        session=session,
        client=GoogleSheetsClient(settings=settings),
    )


def get_web_scraper_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> WebScraperService:
    return WebScraperService(
        session=session,
        client=WebScraperClient(settings=settings),
    )
