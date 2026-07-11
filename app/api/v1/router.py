from fastapi import APIRouter

from app.api.v1.endpoints import agents, google_drive, google_sheets, health, voice, web_scraper

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(google_drive.router, prefix="/google-drive", tags=["google-drive"])
api_router.include_router(google_sheets.router, prefix="/google-sheets", tags=["google-sheets"])
api_router.include_router(web_scraper.router, prefix="/scraper", tags=["scraper"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
