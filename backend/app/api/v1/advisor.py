"""FastAPI router for Indoor Air Advisor and Purifier Sizing endpoint."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.indoor import IndoorAssessmentRequest, IndoorAssessmentResponse
from app.services.indoor_air_service import indoor_air_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisor", tags=["Indoor Advisor"])


@router.post(
    "/indoor-assessment",
    response_model=IndoorAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate deterministic indoor air assessment and purifier sizing",
    description=(
        "Calculates geometrical room volume, evaluates Clean Air Delivery Rate (CADR) in m³/h and CFM, "
        "computes Air Changes per Hour (ACH), and provides prioritized source control and condition-based ventilation advice."
    ),
)
async def assess_indoor_air(request: IndoorAssessmentRequest) -> IndoorAssessmentResponse:
    """Assess indoor room volume, mechanical filtration CADR/ACH, and source controls."""
    try:
        response = await indoor_air_service.assess_room(request)
        return response
    except Exception as e:
        logger.error(f"Error evaluating indoor air assessment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate indoor assessment: {str(e)}",
        )
