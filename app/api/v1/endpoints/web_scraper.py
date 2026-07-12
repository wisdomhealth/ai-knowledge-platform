from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_web_scraper_service
from app.schemas.web_scraper import ScrapeRequest, ScrapeResponse
from app.services.web_scraper_service import WebScraperService

router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(
    payload: ScrapeRequest,
    service: Annotated[WebScraperService, Depends(get_web_scraper_service)],
) -> ScrapeResponse:
    return await service.scrape(payload)
