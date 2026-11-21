"""FastAPI router for Personalized Daily Planner endpoint."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.planner import DailyPlannerRequest, DailyPlannerResponse
from app.services.planner_service import planner_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planner", tags=["Daily Planner"])


@router.post(
    "/generate",
    response_model=DailyPlannerResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate deterministic personalized daily planner recommendations",
    description=(
        "Evaluates household family profile, planned activities, and commute method against "
        "verified ambient air quality from the selected monitoring station using official CPCB/NCDC guidelines."
    ),
)
async def generate_daily_plan(request: DailyPlannerRequest) -> DailyPlannerResponse:
    """Generate personalized daily planner recommendations."""
    try:
        response = await planner_service.generate_plan(request)
        return response
    except Exception as e:
        logger.error(f"Error generating daily plan for station '{request.station_id}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate daily planner: {str(e)}",
        )
