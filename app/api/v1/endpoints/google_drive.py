from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_agent_service, get_google_drive_service
from app.integrations.exceptions import IntegrationNotConfigured
from app.schemas.agents import ConversationRequest
from app.schemas.google_drive import (
    DriveAskRequest,
    DriveAskResponse,
    DriveSearchRequest,
    DriveSearchResponse,
    DriveSyncRequest,
    DriveSyncResponse,
)
from app.services.agent_service import AgentService
from app.services.google_drive_service import GoogleDriveService

router = APIRouter()


@router.post("/sync", response_model=DriveSyncResponse)
async def sync_drive(
    payload: DriveSyncRequest,
    service: GoogleDriveService = Depends(get_google_drive_service),
) -> DriveSyncResponse:
    try:
        return await service.sync(payload)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/search", response_model=DriveSearchResponse)
async def search_drive(
    payload: DriveSearchRequest,
    service: GoogleDriveService = Depends(get_google_drive_service),
) -> DriveSearchResponse:
    return await service.search(payload)


@router.post("/ask", response_model=DriveAskResponse)
async def ask_drive(
    payload: DriveAskRequest,
    service: AgentService = Depends(get_agent_service),
) -> DriveAskResponse:
    response = await service.conversation(
        ConversationRequest(
            message=payload.question,
            conversation_id=payload.conversation_id,
            use_rag=True,
            rag_limit=payload.rag_limit,
        )
    )
    return DriveAskResponse(**response.model_dump())
