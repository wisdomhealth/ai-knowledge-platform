import asyncio
import logging
import re
from dataclasses import replace
from typing import TypedDict

from langgraph.errors import NodeCancelledError
from langgraph.graph import END, START, StateGraph

from app.agents.execution import Execution, public_error, record_interruption
from app.agents.tool_registry import RuntimeContext, ToolRegistry
from app.core.config import Settings
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.agents import WorkflowRequest, WorkflowResponse, WorkflowStep

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    steps: list[WorkflowStep]
    position: int
    status: str
    execution: Execution


class WorkflowAgent:
    def __init__(
        self,
        *,
        repository: ConversationRepository,
        registry: ToolRegistry,
        runtime_context: RuntimeContext,
        settings: Settings | None = None,
    ):
        self.repository = repository
        self.registry = registry
        self.runtime_context = runtime_context
        self.settings = settings or Settings()
        graph = StateGraph(WorkflowState)
        graph.add_node("execute", self._execute)
        graph.add_conditional_edges(START, self._route)
        graph.add_conditional_edges("execute", self._route)
        self.graph = graph.compile()  # No checkpointer, retry policy, or resume path.

    def _route(self, state: WorkflowState) -> str:
        if state["status"] == "failed" or state["position"] >= len(state["steps"]):
            return END
        return "execute"

    async def _execute(self, state: WorkflowState) -> dict:
        execution = state["execution"]
        position = state["position"]
        if position in execution.attempted:
            raise RuntimeError("Refusing to execute a workflow step twice.")
        execution.attempted.add(position)
        step = state["steps"][position]
        tool = await self.repository.start_tool_execution(
            agent_run_id=execution.run_id,
            tool_name=step.tool_name,
            arguments=step.arguments,
        )
        execution.tool_id, execution.tool_name = tool.id, step.tool_name
        execution.dispatched = False
        execution.tool_result = None
        status = "completed"

        def confirmed(result: dict) -> None:
            execution.tool_result = result

        context = replace(self.runtime_context, on_write_confirmed=confirmed)
        try:
            self.registry.validate(step.tool_name, step.arguments)
            execution.dispatched = True
            async with asyncio.timeout(self.settings.call_timeout_seconds):
                result = await self.registry.execute(
                    name=step.tool_name,
                    arguments=step.arguments,
                    context=context,
                )
        except (TimeoutError, asyncio.CancelledError):
            raise
        except Exception as exc:
            status = "failed"
            confirmed_result = execution.tool_result is not None
            uncertain = (
                step.tool_name == "sheets.append" and execution.dispatched and not confirmed_result
            )
            error = (
                "Write outcome uncertain; verify Google Sheets manually before retrying."
                if uncertain
                else public_error(exc)
            )
            await self.repository.session.rollback()
            await self.repository.finish_tool_execution(
                execution.tool_id,
                status="completed" if confirmed_result else "uncertain" if uncertain else "failed",
                result=execution.tool_result,
                error=None if confirmed_result else error,
            )
            execution.results.append(
                {
                    "tool": step.tool_name,
                    "error": error,
                    **({"result": execution.tool_result} if confirmed_result else {}),
                }
            )
            execution.trace.append(
                {
                    "step": position,
                    "tool": step.tool_name,
                    "status": "completed"
                    if confirmed_result
                    else "uncertain"
                    if uncertain
                    else "failed",
                    "error": error,
                }
            )
            logger.warning(
                "tool_failed run_id=%s step=%s error_type=%s",
                execution.run_id,
                position,
                type(exc).__name__,
            )
        else:
            execution.tool_result = result
            await self.repository.finish_tool_execution(tool.id, status="completed", result=result)
            execution.results.append({"tool": step.tool_name, "result": result})
            execution.trace.append(
                {"step": position, "tool": step.tool_name, "status": "completed"}
            )
        execution.tool_id = None
        return {"position": position + 1, "status": status}

    async def run(self, payload: WorkflowRequest) -> WorkflowResponse:
        execution = None
        try:
            async with asyncio.timeout(self.settings.execution_timeout_seconds):
                steps = payload.steps or self._infer_steps(payload.goal)
                run = await self.repository.create_agent_run(
                    agent_type="workflow",
                    conversation_id=payload.conversation_id,
                    goal=payload.goal,
                    input_json=payload.model_dump(mode="json"),
                )
                execution = Execution(run.id)
                await self.repository.session.commit()
                if len(steps) > self.settings.max_tool_steps:
                    status = "failed"
                    execution.trace.append(
                        {"event": "step_limit", "error": "Maximum tool steps exceeded."}
                    )
                else:
                    state = await self.graph.ainvoke(
                        {
                            "steps": steps,
                            "position": 0,
                            "status": "completed",
                            "execution": execution,
                        },
                        config={"recursion_limit": self.settings.max_tool_steps + 2},
                    )
                    status = state["status"]
                    if not steps:
                        execution.trace.append(
                            {"event": "no_steps", "reason": "No explicit or inferred tool steps."}
                        )
                await self.repository.finish_run(
                    execution.run_id,
                    status=status,
                    output={"results": execution.results},
                    trace=execution.trace,
                )
                return WorkflowResponse(
                    run_id=execution.run_id,
                    status=status,
                    results=execution.results,
                    trace=execution.trace,
                )
        except (Exception, asyncio.CancelledError) as exc:
            if isinstance(exc, NodeCancelledError):
                exc = asyncio.CancelledError()
            if execution is not None:
                await record_interruption(self.repository, execution, exc)
            else:
                await self.repository.session.rollback()
            raise exc

    def _infer_steps(self, goal: str) -> list[WorkflowStep]:
        url_match = re.search(r"https?://\S+", goal)
        if url_match:
            return [WorkflowStep(tool_name="web.scrape", arguments={"url": url_match.group(0)})]
        return []
