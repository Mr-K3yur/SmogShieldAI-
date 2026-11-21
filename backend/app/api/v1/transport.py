"""FastAPI router for Transportation Advisor and Emission Factor Registry."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.transport import (
    EmissionFactorRegistryResponse,
    TransportComparisonRequest,
    TransportComparisonResponse,
)
from app.services.emission_factor_registry import emission_factor_registry
from app.services.transport_service import transport_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transport", tags=["Transportation Advisor"])


@router.get(
    "/emission-factors",
    response_model=EmissionFactorRegistryResponse,
    status_code=status.HTTP_200_OK,
    summary="Read audited emission factor registry",
    description="Returns exactly 9 audited emission factor entries with source citations, base and uplifted values, and boundaries."
)
def get_emission_factors(
    mode: Optional[str] = Query(default=None, description="Optional mode filter"),
    fuel_type: Optional[str] = Query(default=None, description="Optional fuel type filter"),
) -> EmissionFactorRegistryResponse:
    """Read the static audited emission factor registry."""
    factors = emission_factor_registry.get_all_factors()
    if mode:
        factors = [f for f in factors if f.mode == mode]
    if fuel_type:
        factors = [f for f in factors if f.fuel_type == fuel_type]

    return EmissionFactorRegistryResponse(
        total_factors=len(factors),
        factors=factors,
        registry_notes=[
            "All road transport factors are sourced from India GHG Program (2015) stakeholder consultation paper and carry HISTORICAL_PROVISIONAL status.",
            "CEA electricity grid factor reflects Version 22.0 (FY 2025-26) and serves as a prior-year estimate for FY 2026-27.",
            "Indian Railways rail factor explicitly excludes Mass Rapid Transit Systems (Metro) per source documentation.",
            "All values represent direct operational tailpipe CO2 only (not CO2e).",
        ]
    )


@router.post(
    "/compare",
    response_model=TransportComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare transport modes with AQI integration",
    description="Evaluates baseline commute travel against alternative modes using verified Phase 3 AQI data and Phase 4 NCDC health advisories."
)
async def compare_transport_modes(request: TransportComparisonRequest) -> TransportComparisonResponse:
    """Run deterministic transport comparison and health advisory evaluation."""
    try:
        return await transport_service.compare_transport_modes(request)
    except Exception as e:
        logger.error(f"Error during transport mode comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare transport modes: {str(e)}"
        )
