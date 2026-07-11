from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.web_scraper import WebScraperClient
from app.repositories.document_repository import DocumentRepository
from app.schemas.web_scraper import ScrapeRequest, ScrapeResponse


class WebScraperService:
    def __init__(self, *, session: AsyncSession, client: WebScraperClient):
        self.session = session
        self.client = client
        self.documents = DocumentRepository(session)

    async def scrape(self, payload: ScrapeRequest) -> ScrapeResponse:
        content = await self.client.scrape(str(payload.url))
        page = await self.documents.record_scraped_page(
            url=content.url,
            title=content.title,
            text_content=content.text,
            status_code=content.status_code,
            metadata={"content_type": content.content_type},
        )
        await self.session.commit()
        return ScrapeResponse(
            page_id=page.id,
            url=page.url,
            title=page.title,
            text=page.text_content[:20000],
            status_code=page.status_code,
            content_hash=page.content_hash,
            content_type=content.content_type,
        )
