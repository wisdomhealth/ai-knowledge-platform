from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.core.config import Settings


@dataclass(frozen=True)
class ScrapedContent:
    url: str
    status_code: int
    title: str | None
    text: str
    content_type: str | None


class WebScraperClient:
    def __init__(self, *, settings: Settings):
        self.settings = settings

    async def scrape(self, url: str) -> ScrapedContent:
        headers = {"User-Agent": self.settings.scraper_user_agent}
        timeout = httpx.Timeout(self.settings.scraper_timeout_seconds)
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else None
        text = " ".join(part.strip() for part in soup.stripped_strings if part.strip())

        return ScrapedContent(
            url=str(response.url),
            status_code=response.status_code,
            title=title,
            text=text,
            content_type=response.headers.get("content-type"),
        )
