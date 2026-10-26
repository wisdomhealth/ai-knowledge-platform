"""Request-scoped execution bookkeeping; no checkpointing or automatic retries."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.integrations.exceptions import IndexIncompatible, ToolNotFound
from app.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)


@dataclass
class Execution:
    run_id: uuid.UUID
    attempted: set[int] = field(default_factory=set)
    tool_id: uuid.UUID | None = None
    tool_name: str | None = None
    dispatched: bool = False
    tool_result: dict | None = None
    results: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)


def public_error(exc: BaseException) -> str:
    if isinstance(exc, ToolNotFound):
        return "Unknown tool."
    if isinstance(exc, ValidationError):
        return "Invalid tool arguments."
    if isinstance(exc, IndexIncompatible):
        return "Index incompatible: verify embedding identity and dimensions before use."
    if isinstance(exc, TimeoutError):
        return "Execution timed out."
    if isinstance(exc, asyncio.CancelledError):
        return "Execution cancelled."
    return "Operation failed. Check the server logs using the run ID."


async def record_interruption(
    repository: ConversationRepository,
    execution: Execution,
    exc: BaseException,
) -> None:
    """Bound audit cleanup separately, then let the caller re-raise the signal.

    This cannot guarantee persistence during database outages or process death.
    A failed cleanup is logged using identifiers only, never external payloads.
    """

    async def save() -> None:
        async with asyncio.timeout(5):
            await repository.session.rollback()
            error = public_error(exc)
            if execution.tool_id is not None:
                confirmed = execution.tool_result is not None
                uncertain = (
                    execution.tool_name == "sheets.append"
                    and execution.dispatched
                    and not confirmed
                )
                if uncertain:
                    error = (
                        "Write outcome uncertain; verify Google Sheets manually before retrying."
                    )
                status = "completed" if confirmed else "uncertain" if uncertain else "failed"
                await repository.finish_tool_execution(
                    execution.tool_id,
                    status=status,
                    result=execution.tool_result,
                    error=None if confirmed else error,
                )
                event = {"tool": execution.tool_name, "status": status}
                if confirmed:
                    execution.results.append(
                        {"tool": execution.tool_name, "result": execution.tool_result}
                    )
                else:
                    event["error"] = error
                    execution.results.append({"tool": execution.tool_name, "error": error})
                execution.trace.append(event)
            await repository.finish_run(
                execution.run_id,
                status="cancelled" if isinstance(exc, asyncio.CancelledError) else "failed",
                output={"error": error, "results": execution.results},
                trace=execution.trace,
            )

    cleanup = asyncio.create_task(save())
    try:
        await asyncio.shield(cleanup)
    except (Exception, asyncio.CancelledError):
        # Avoid leaving a background task using a request session after it closes.
        cleanup.cancel()
        try:
            await cleanup
        except (Exception, asyncio.CancelledError):
            pass
        logger.error("audit_cleanup_failed run_id=%s", execution.run_id)
    logger.warning(
        "agent_interrupted run_id=%s error_type=%s", execution.run_id, type(exc).__name__
    )
