from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_google_sheets_service
from app.integrations.exceptions import IntegrationNotConfigured
from app.schemas.google_sheets import (
    SheetAppendRequest,
    SheetAppendResponse,
    SheetReadRequest,
    SheetReadResponse,
)
from app.services.google_sheets_service import GoogleSheetsService

router = APIRouter()


@router.post("/read", response_model=SheetReadResponse)
async def read_sheet_range(
    payload: SheetReadRequest,
    service: Annotated[GoogleSheetsService, Depends(get_google_sheets_service)],
) -> SheetReadResponse:
    try:
        return await service.read_range(payload)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/append", response_model=SheetAppendResponse)
async def append_sheet_rows(
    payload: SheetAppendRequest,
    service: Annotated[GoogleSheetsService, Depends(get_google_sheets_service)],
) -> SheetAppendResponse:
    try:
        return await service.append_rows(payload)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
