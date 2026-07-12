from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_agent_service
from app.schemas.agents import (
    ConversationRequest,
    ConversationResponse,
    WorkflowRequest,
    WorkflowResponse,
)
from app.services.agent_service import AgentService

router = APIRouter()


@router.post("/conversation", response_model=ConversationResponse)
async def conversation_agent(
    payload: ConversationRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> ConversationResponse:
    return await service.conversation(payload)


@router.post("/workflow", response_model=WorkflowResponse)
async def workflow_agent(
    payload: WorkflowRequest,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> WorkflowResponse:
    return await service.workflow(payload)
