import re
from typing import Any

from app.agents.tool_registry import RuntimeContext, ToolRegistry
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.agents import WorkflowRequest, WorkflowResponse, WorkflowStep


class WorkflowAgent:
    """Execute workflow tool steps in order and persist results and traces.

    Constructor arguments:
        repository: Data access object that stores agent runs and tool executions.
        registry: Tool registry that resolves and executes handlers by name.
        runtime_context: RAG, web scraping, and Sheets services used by tools.
    """

    def __init__(
        self,
        *,
        repository: ConversationRepository,
        registry: ToolRegistry,
        runtime_context: RuntimeContext,
    ):
        self.repository = repository
        self.registry = registry
        self.runtime_context = runtime_context

    async def run(self, payload: WorkflowRequest) -> WorkflowResponse:
        steps = payload.steps or self._infer_steps(payload.goal)
        agent_run = await self.repository.create_agent_run(
            agent_type="workflow",
            conversation_id=payload.conversation_id,
            goal=payload.goal,
            input_json=payload.model_dump(mode="json"),
        )

        results: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        status = "completed"

        for position, step in enumerate(steps):
            try:
                result = await self.registry.execute(
                    name=step.tool_name,
                    arguments=step.arguments,
                    context=self.runtime_context,
                )
                await self.repository.add_tool_execution(
                    agent_run_id=agent_run.id,
                    tool_name=step.tool_name,
                    arguments=step.arguments,
                    result=result,
                    status="completed",
                )
                event = {"step": position, "tool": step.tool_name, "status": "completed"}
                results.append({"tool": step.tool_name, "result": result})
                trace.append(event)
            except Exception as exc:  # noqa: BLE001
                status = "failed"
                error = str(exc)
                await self.repository.add_tool_execution(
                    agent_run_id=agent_run.id,
                    tool_name=step.tool_name,
                    arguments=step.arguments,
                    status="failed",
                    error=error,
                )
                trace.append(
                    {
                        "step": position,
                        "tool": step.tool_name,
                        "status": "failed",
                        "error": error,
                    }
                )
                results.append({"tool": step.tool_name, "error": error})
                break

        if not steps:
            status = "completed"
            trace.append({"event": "no_steps", "reason": "No explicit or inferred tool steps."})

        await self.repository.complete_agent_run(
            agent_run,
            status=status,
            output_json={"results": results},
            trace=trace,
        )
        return WorkflowResponse(run_id=agent_run.id, status=status, results=results, trace=trace)

    def _infer_steps(self, goal: str) -> list[WorkflowStep]:
        url_match = re.search(r"https?://\S+", goal)
        if url_match:
            return [WorkflowStep(tool_name="web.scrape", arguments={"url": url_match.group(0)})]
        return []
