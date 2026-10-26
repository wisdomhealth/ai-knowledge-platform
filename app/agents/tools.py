from typing import Any

from pydantic import BaseModel, Field

from app.agents.tool_registry import RuntimeContext, ToolDefinition, ToolHandler, ToolRegistry
from app.schemas.google_sheets import SheetAppendRequest, SheetReadRequest
from app.schemas.web_scraper import ScrapeRequest


async def rag_search(arguments: dict[str, Any], context: RuntimeContext) -> dict[str, Any]:
    query = str(arguments.get("query", ""))
    limit = int(arguments.get("limit", 5))
    results = await context.rag_service.search(query=query, limit=limit)
    return {
        "results": [
            {
                "document_id": str(item.document_id) if item.document_id else None,
                "chunk_id": str(item.chunk_id) if item.chunk_id else None,
                "title": item.title,
                "content": item.content,
                "score": item.score,
            }
            for item in results
        ]
    }


async def web_scrape(arguments: dict[str, Any], context: RuntimeContext) -> dict[str, Any]:
    response = await context.web_scraper_service.scrape(ScrapeRequest(url=arguments["url"]))
    return response.model_dump(mode="json")


async def sheets_read(arguments: dict[str, Any], context: RuntimeContext) -> dict[str, Any]:
    response = await context.google_sheets_service.read_range(SheetReadRequest(**arguments))
    return response.model_dump(mode="json")


async def sheets_append(arguments: dict[str, Any], context: RuntimeContext) -> dict[str, Any]:
    response = await context.google_sheets_service.append_rows(
        SheetAppendRequest(**arguments), on_confirmed=context.on_write_confirmed
    )
    return response.model_dump(mode="json")


class RagSearchArguments(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    definitions: list[tuple[str, str, type[BaseModel], ToolHandler]] = [
        ("rag.search", "Search indexed knowledge-base documents.", RagSearchArguments, rag_search),
        ("web.scrape", "Fetch and extract a web page.", ScrapeRequest, web_scrape),
        ("sheets.read", "Read a Google Sheets range.", SheetReadRequest, sheets_read),
        ("sheets.append", "Append rows to Google Sheets.", SheetAppendRequest, sheets_append),
    ]
    for name, description, schema, handler in definitions:
        registry.register(
            ToolDefinition(
                name=name,
                description=description,
                args_schema=schema,
                handler=handler,
            )
        )
    return registry
