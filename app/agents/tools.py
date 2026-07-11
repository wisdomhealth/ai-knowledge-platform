from typing import Any

from app.agents.tool_registry import RuntimeContext, ToolDefinition, ToolRegistry
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
    response = await context.google_sheets_service.append_rows(SheetAppendRequest(**arguments))
    return response.model_dump(mode="json")


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="rag.search",
            description="Search indexed Google Drive and web documents.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            handler=rag_search,
        )
    )
    registry.register(
        ToolDefinition(
            name="web.scrape",
            description="Fetch a web page and extract readable text.",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string", "format": "uri"}},
                "required": ["url"],
            },
            handler=web_scrape,
        )
    )
    registry.register(
        ToolDefinition(
            name="sheets.read",
            description="Read values from a Google Sheets range.",
            parameters={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string"},
                    "range_name": {"type": "string"},
                },
                "required": ["spreadsheet_id", "range_name"],
            },
            handler=sheets_read,
        )
    )
    registry.register(
        ToolDefinition(
            name="sheets.append",
            description="Append rows to a Google Sheets range.",
            parameters={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string"},
                    "range_name": {"type": "string"},
                    "values": {"type": "array", "items": {"type": "array"}},
                },
                "required": ["spreadsheet_id", "range_name", "values"],
            },
            handler=sheets_append,
        )
    )
    return registry
