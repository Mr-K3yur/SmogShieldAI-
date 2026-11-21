from typing import Optional
from fastapi import APIRouter, Path, Query
from app.schemas.station import StationAQIResponse, StationListResponse
from app.services.station_service import station_service

router = APIRouter(prefix="/aqi", tags=["Air Quality Ingestion & Stations"])


@router.get("/stations", response_model=StationListResponse)
async def list_stations(
    city: Optional[str] = Query(
        None,
        description="Filter stations by city name (e.g. Delhi, Mumbai, Bengaluru, Lucknow, Patna)",
    ),
    provider: Optional[str] = Query(
        None,
        description="Filter by provider: 'cpcb_datagov', 'openaq', or 'mock'",
    ),
) -> StationListResponse:
    """Discover monitoring stations with verified metadata from configured providers.

    Supports city-based search and provider filtering. Respects explicit DEMO_MODE setting.
    """
    return await station_service.list_stations(city=city, provider_name=provider)


@router.get("/station/{station_id}", response_model=StationAQIResponse)
async def get_station_aqi(
    station_id: str = Path(
        ...,
        description="Provider-prefixed station ID (e.g. cpcb_delhi_ito, openaq_12345, mock_delhi_ito)",
    ),
) -> StationAQIResponse:
    """Retrieve the latest air quality report for a specific monitoring station.

    Enforces strict separation of Provenance (PROVIDER_REPORTED, CALCULATED, SIMULATED_DEMO),
    Availability (AVAILABLE, UNAVAILABLE), and Freshness (FRESH, STALE, EXPIRED, DEMO).
    Preserves original sensor IDs, units, and timestamps.
    """
    return await station_service.get_station_aqi(station_id)
