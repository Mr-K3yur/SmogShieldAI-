"""FastAPI router for Environmental Impact Tracker and Session Management."""

import logging
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, status

from app.schemas.impact import (
    ImpactSessionSummary,
    SessionCreationResponse,
    TripLogEntry,
    TripLogResult,
)
from app.services.impact_service import impact_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/impact", tags=["Environmental Impact Tracker"])


@router.post(
    "/sessions",
    response_model=SessionCreationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new isolated in-memory impact tracking session",
    description="Issues a server-generated UUID4 session bearer token valid for 24 hours of inactivity."
)
def create_session() -> SessionCreationResponse:
    """Create a new session."""
    return impact_service.create_session()


@router.post(
    "/log-trip",
    response_model=TripLogResult,
    status_code=status.HTTP_201_CREATED,
    summary="Log a completed sustainable or commute trip",
    description="Calculates 100% of emissions server-side with idempotency protection and baseline comparison."
)
async def log_completed_trip(
    entry: TripLogEntry,
    x_session_id: str = Header(..., description="Server-issued session bearer token"),
    idempotency_key: str = Header(..., description="Client-supplied unique request key for duplicate protection"),
) -> TripLogResult:
    """Deterministically record a completed trip into memory."""
    try:
        return await impact_service.log_completed_trip(
            session_id=x_session_id,
            entry=entry,
            idempotency_key=idempotency_key,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging trip for session '{x_session_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record completed trip: {str(e)}"
        )


@router.get(
    "/session-summary",
    response_model=ImpactSessionSummary,
    status_code=status.HTTP_200_OK,
    summary="Get comprehensive impact summary for an active session",
    description="Returns actual completed trip totals, weekly summaries, and monthly summaries (never extrapolated)."
)
def get_session_summary(
    x_session_id: str = Header(..., description="Server-issued session bearer token")
) -> ImpactSessionSummary:
    """Retrieve session impact summary."""
    try:
        return impact_service.get_session_summary(x_session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session summary for '{x_session_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session summary: {str(e)}"
        )
