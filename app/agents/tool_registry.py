from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeContext:
    """Provide service dependencies available during tool execution.

    Constructor arguments:
        rag_service: Service that provides knowledge-base retrieval.
        web_scraper_service: Service that provides web scraping.
        google_sheets_service: Service that provides Google Sheets read and write access.
    """

    rag_service: Any
    web_scraper_service: Any
    google_sheets_service: Any


ToolHandler = Callable[[dict[str, Any], RuntimeContext], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    """Describe an agent tool that can be registered and executed.

    Constructor arguments:
        name: Unique name of the tool.
        description: Description of the tool's purpose.
        parameters: JSON Schema definition of the tool arguments.
        handler: Async handler that receives arguments and a runtime context.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler


class ToolRegistry:
    """Manage agent tool registration, lookup, and execution.

    The constructor accepts no arguments and initializes an empty tool mapping.
    """

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
