from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings
from app.schemas.health import HealthResponse
from app import __version__

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return system operational status and runtime configuration."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=__version__,
        timestamp_utc=datetime.now(timezone.utc),
        environment=settings.APP_ENV,
        gemini_model_configured=settings.GEMINI_MODEL
    )
