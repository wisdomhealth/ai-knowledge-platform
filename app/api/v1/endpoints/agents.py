from collections.abc import Awaitable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_agent_service
from app.integrations.exceptions import IndexIncompatible
from app.schemas.agents import (
    ConversationRequest,
    ConversationResponse,
    WorkflowRequest,
    WorkflowResponse,
)
from app.services.agent_service import AgentService

router = APIRouter()


async def _run_agent[Response](operation: Awaitable[Response]) -> Response:
    try:
        return await operation
    except IndexIncompatible as exc:
        raise HTTPException(409, "Index incompatible: verify embedding configuration.") from exc
    except TimeoutError as exc:
        raise HTTPException(
            504, "Agent execution timed out; inspect run records before retrying."
        ) from exc
    except Exception as exc:
        raise HTTPException(
            502, "Agent execution failed; inspect run records for details."
        ) from exc


@router.post("/conversation", response_model=ConversationResponse)
async def conversation_agent(
    payload: ConversationRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> ConversationResponse:
    return await _run_agent(service.conversation(payload))


@router.post("/workflow", response_model=WorkflowResponse)
async def workflow_agent(
    payload: WorkflowRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> WorkflowResponse:
    return await _run_agent(service.workflow(payload))
