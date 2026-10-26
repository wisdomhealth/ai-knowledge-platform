from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.integrations.exceptions import ToolNotFound


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
    on_write_confirmed: Callable[[dict[str, Any]], None] | None = None


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
    args_schema: type[BaseModel]
    handler: ToolHandler

    @property
    def parameters(self) -> dict[str, Any]:
        return self.args_schema.model_json_schema()


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

    def validate(self, name: str, arguments: dict[str, Any]) -> None:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFound("Unknown tool.")
        tool.args_schema.model_validate(arguments)

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
            raise ToolNotFound(f"Unknown tool '{name}'. Available tools: {available}")

        async def invoke(**kwargs: Any) -> dict[str, Any]:
            return await tool.handler(kwargs, context)

        adapter = StructuredTool.from_function(
            coroutine=invoke,
            name=tool.name,
            description=tool.description,
            args_schema=tool.args_schema,
        )
        return await adapter.ainvoke(arguments)
