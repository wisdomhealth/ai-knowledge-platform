from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeContext:
    rag_service: Any
    web_scraper_service: Any
    google_sheets_service: Any


ToolHandler = Callable[[dict[str, Any], RuntimeContext], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    async def execute(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        context: RuntimeContext,
    ) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools))
            raise ValueError(f"Unknown tool '{name}'. Available tools: {available}")
        return await tool.handler(arguments, context)
