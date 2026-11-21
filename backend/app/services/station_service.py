"""Station Ingestion and Provenance Orchestration Service for SmogShield AI.

Integrates:
1. Multi-provider measurement retrieval (DataGovINProvider, OpenAQProvider, MockAQIProvider)
2. Freshness evaluation via StalenessService
3. Phase 2 CPCB NAQI calculation engine integration
4. Strict separation of Provenance, Availability, and Freshness
5. Preservation of both provider-reported and locally calculated AQI
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

from app.config import settings
from app.core.cpcb_naqi import compute_station_cpcb_aqi
from app.schemas.station import (
    AvailabilityType,
    FreshnessType,
    ProvenanceType,
    StationAQIResponse,
    StationMetadata,
    StationPollutantMeasurement,
    StationListResponse,
)
from app.services.aqi_provider import (
    BaseAQIProvider,
    DataGovINProvider,
    MockAQIProvider,
    OpenAQProvider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    get_provider_for_station,
)
from app.services.staleness_service import evaluate_freshness, to_ist_string

logger = logging.getLogger(__name__)


class StationService:
    """Coordinates station discovery, data fetching, validation, and AQI computation."""

    def __init__(self, provider: Optional[BaseAQIProvider] = None):
        self._default_provider = provider

    def _resolve_provider(self, station_id: Optional[str] = None) -> BaseAQIProvider:
        if self._default_provider is not None:
            return self._default_provider
        if station_id:
            return get_provider_for_station(station_id)
        if settings.DEMO_MODE:
            return MockAQIProvider()
        return DataGovINProvider()

    async def list_stations(
        self, city: Optional[str] = None, provider_name: Optional[str] = None
    ) -> StationListResponse:
        """Discover monitoring stations, respecting demo mode and provider selection."""
        warnings: List[str] = []
        is_demo = settings.DEMO_MODE or (provider_name == "mock")

        if is_demo:
            provider: BaseAQIProvider = MockAQIProvider()
            warnings.append("DEMO MODE ACTIVE: Showing simulated monitoring stations.")
        elif provider_name == "openaq":
            provider = OpenAQProvider()
        else:
            provider = DataGovINProvider()

        try:
            stations = await provider.discover_stations(city=city)
        except ProviderAuthError as auth_err:
            stations = []
            warnings.append(str(auth_err))
        except ProviderError as prov_err:
            stations = []
            warnings.append(str(prov_err))
        except Exception as e:
            stations = []
            warnings.append(f"Unexpected provider error during station discovery: {str(e)}")

        return StationListResponse(
            total=len(stations),
            stations=stations,
            provider=provider.provider_name,
            demo_mode=is_demo,
            warnings=warnings,
        )

    async def get_station_aqi(self, station_id: str) -> StationAQIResponse:
        """Fetch station data, evaluate freshness, run CPCB calculation, and build response."""
        provider = self._resolve_provider(station_id)
        fetched_at_utc = datetime.now(timezone.utc)
        is_demo = settings.DEMO_MODE or (provider.provider_name == "mock")

        try:
            (
                metadata,
                measurements,
                provider_aqi,
                provider_cat,
                obs_dt,
                provider_warnings,
            ) = await provider.get_latest_measurements(station_id)
        except ProviderAuthError as auth_err:
            return self._build_unavailable_response(
                station_id=station_id,
                reason=str(auth_err),
                fetched_at_utc=fetched_at_utc,
                warnings=[str(auth_err)],
            )
        except ProviderRateLimitError as rate_err:
            return self._build_unavailable_response(
                station_id=station_id,
                reason=str(rate_err),
                fetched_at_utc=fetched_at_utc,
                warnings=[str(rate_err)],
            )
        except ProviderError as prov_err:
            return self._build_unavailable_response(
                station_id=station_id,
                reason=str(prov_err),
                fetched_at_utc=fetched_at_utc,
                warnings=[str(prov_err)],
            )
        except Exception as err:
            return self._build_unavailable_response(
                station_id=station_id,
                reason=f"Failed to fetch data from provider: {str(err)}",
                fetched_at_utc=fetched_at_utc,
                warnings=[str(err)],
            )

        if not metadata:
            return self._build_unavailable_response(
                station_id=station_id,
                reason=f"Station '{station_id}' was not found in provider registry.",
                fetched_at_utc=fetched_at_utc,
                warnings=provider_warnings,
            )

        # 1. Freshness Evaluation
        freshness, freshness_msg = evaluate_freshness(
            observed_at=obs_dt,
            now_utc=fetched_at_utc,
            fresh_hours=settings.FRESH_THRESHOLD_HOURS,
            stale_hours=settings.STALE_THRESHOLD_HOURS,
            is_demo=is_demo,
        )

        all_warnings: List[str] = list(provider_warnings)
        if freshness_msg and freshness != FreshnessType.FRESH and freshness != FreshnessType.DEMO:
            all_warnings.append(freshness_msg)

        # Update freshness on individual measurements
        for m in measurements.values():
            m.freshness = freshness

        # 2. Run Phase 2 CPCB NAQI calculation engine on qualifying measurements
        calc_payload = [
            {
                "pollutant": m.pollutant,
                "value": m.value,
                "unit": m.unit,
                "averaging_hours": m.averaging_period_hours,
                "hours_recorded": m.coverage_hours,
            }
            for m in measurements.values()
        ]
        calc_result = compute_station_cpcb_aqi(calc_payload)

        calculated_aqi = calc_result.get("overall_aqi")
        is_calc_eligible = calc_result.get("eligible_for_overall_aqi", False)

        # 3. Determine Provenance, Availability, and Active AQI
        overall_aqi: Optional[int] = None
        overall_aqi_lb: Optional[int] = None
        overall_aqi_ub: Optional[int] = None
        is_exact = False
        category = "Unknown"
        dominant_pollutant: Optional[str] = None
        unavailable_reason: Optional[str] = None

        if is_demo:
            provenance = ProvenanceType.SIMULATED_DEMO
            freshness = FreshnessType.DEMO
            all_warnings.append("SIMULATED DATA - NOT LIVE AQI")
            provider_aqi = None  # Rule: Never populate provider_reported_aqi with a simulated number
            provider_cat = None

            if is_calc_eligible:
                availability = AvailabilityType.AVAILABLE
                overall_aqi = calc_result.get("overall_aqi")
                overall_aqi_lb = calc_result.get("overall_aqi_lower_bound")
                overall_aqi_ub = calc_result.get("overall_aqi_upper_bound")
                is_exact = calc_result.get("is_exact", False)
                category = calc_result.get("category", "Unknown")
                dominant_pollutant = calc_result.get("dominant_pollutant")
            else:
                availability = AvailabilityType.UNAVAILABLE
                overall_aqi = None
                calculated_aqi = None
                unavailable_reason = calc_result.get(
                    "reason", "Insufficient qualifying simulated pollutants per CPCB criteria."
                )
        elif freshness == FreshnessType.EXPIRED:
            # Expired data (>24h): Never call live! Mark UNAVAILABLE.
            provenance = ProvenanceType.NONE
            availability = AvailabilityType.UNAVAILABLE
            unavailable_reason = (
                f"Data is EXPIRED (> {settings.STALE_THRESHOLD_HOURS:.0f} hours old). "
                "CPCB guidelines require recent monitoring data; expired readings cannot be used as live AQI."
            )
            all_warnings.append(unavailable_reason)
        elif provider_aqi is not None:
            # Official CPCB provider-reported scalar AQI takes precedence
            provenance = ProvenanceType.PROVIDER_REPORTED
            availability = AvailabilityType.AVAILABLE
            overall_aqi = provider_aqi
            overall_aqi_lb = provider_aqi
            overall_aqi_ub = provider_aqi
            is_exact = True
            category = provider_cat or calc_result.get("category", "Unknown")
            dominant_pollutant = calc_result.get("dominant_pollutant")
        elif is_calc_eligible:
            # Computed locally via CPCB NAQI engine
            provenance = ProvenanceType.CALCULATED
            availability = AvailabilityType.AVAILABLE
            overall_aqi = calc_result.get("overall_aqi")
            overall_aqi_lb = calc_result.get("overall_aqi_lower_bound")
            overall_aqi_ub = calc_result.get("overall_aqi_upper_bound")
            is_exact = calc_result.get("is_exact", False)
            category = calc_result.get("category", "Unknown")
            dominant_pollutant = calc_result.get("dominant_pollutant")
        else:
            # Insufficient pollutant data for overall AQI
            provenance = ProvenanceType.NONE
            availability = AvailabilityType.UNAVAILABLE
            unavailable_reason = calc_result.get(
                "reason", "Insufficient qualifying pollutant coverage per CPCB criteria."
            )

        # Remove duplicate warnings while preserving order
        unique_warnings = list(dict.fromkeys(all_warnings))

        return StationAQIResponse(
            station=metadata,
            provenance=provenance,
            availability=availability,
            freshness=freshness,
            provider_reported_aqi=provider_aqi,
            provider_reported_category=provider_cat,
            calculated_aqi=calculated_aqi,
            overall_aqi=overall_aqi,
            overall_aqi_lower_bound=overall_aqi_lb,
            overall_aqi_upper_bound=overall_aqi_ub,
            is_exact=is_exact,
            category=category,
            dominant_pollutant=dominant_pollutant,
            pollutant_measurements=measurements,
            source=f"{metadata.provider} ({metadata.station_name})",
            observed_at_utc=obs_dt,
            observed_at_ist=to_ist_string(obs_dt),
            fetched_at_utc=fetched_at_utc,
            warnings=unique_warnings,
            unavailable_reason=unavailable_reason,
        )

    def _build_unavailable_response(
        self,
        station_id: str,
        reason: str,
        fetched_at_utc: datetime,
        warnings: List[str],
    ) -> StationAQIResponse:
        """Create fallback StationAQIResponse when station data cannot be fetched."""
        stub_meta = StationMetadata(
            station_id=station_id,
            provider="unknown",
            provider_station_id=station_id,
            station_name=f"Station {station_id}",
            city="Unknown",
            state="Unknown",
        )
        return StationAQIResponse(
            station=stub_meta,
            provenance=ProvenanceType.NONE,
            availability=AvailabilityType.UNAVAILABLE,
            freshness=FreshnessType.UNKNOWN,
            source="Provider Error",
            fetched_at_utc=fetched_at_utc,
            warnings=warnings,
            unavailable_reason=reason,
        )


station_service = StationService()
