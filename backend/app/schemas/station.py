from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ProvenanceType(str, Enum):
    """Origin and calculation authority of the reported AQI."""
    PROVIDER_REPORTED = "PROVIDER_REPORTED"  # Official scalar AQI published by CPCB/data.gov.in
    CALCULATED = "CALCULATED"                # Computed locally via CPCB NAQI formula from qualified raw pollutants
    SIMULATED_DEMO = "SIMULATED_DEMO"        # Explicitly marked offline test/demo dataset
    NONE = "NONE"                            # Neither provider nor local engine could produce AQI


class AvailabilityType(str, Enum):
    """Whether sufficient monitoring data exists to present an overall AQI."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class FreshnessType(str, Enum):
    """Application freshness classification based on time elapsed since observation.
    
    Default application policy:
      - FRESH: <= 4 hours
      - STALE: > 4 hours and <= 24 hours
      - EXPIRED: > 24 hours
      - DEMO: Explicit test simulation
    """
    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    DEMO = "DEMO"
    UNKNOWN = "UNKNOWN"


class ProviderType(str, Enum):
    """External data provider identifiers."""
    DATA_GOV_IN = "cpcb_datagov"
    OPENAQ = "openaq"
    MOCK = "mock"


class StationMetadata(BaseModel):
    """Normalized metadata for a physical or virtual air quality monitoring station."""
    station_id: str = Field(..., description="Unique provider-prefixed station identifier, e.g. cpcb_delhi_ito")
    provider: str = Field(..., description="Source provider (e.g. cpcb_datagov, openaq, mock)")
    provider_station_id: str = Field(..., description="Original raw station ID from the upstream provider")
    station_name: str = Field(..., description="Human-readable name of the station")
    city: str = Field(..., description="City or district (e.g. Delhi, Mumbai, Bengaluru)")
    state: str = Field(..., description="State or Union Territory (e.g. Delhi, Maharashtra)")
    latitude: Optional[float] = Field(default=None, description="Geographic latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Geographic longitude coordinate")
    country: str = Field(default="India", description="Country name")
    timezone: str = Field(default="Asia/Kolkata", description="Local station timezone")


class StationPollutantMeasurement(BaseModel):
    """An individual criteria pollutant measurement tied to a specific sensor stream."""
    pollutant: str = Field(..., description="Standard criteria pollutant name (e.g. PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb)")
    sensor_id: Optional[str] = Field(default=None, description="Upstream sensor ID (critical for OpenAQ v3 preservation)")
    value: float = Field(..., description="Measured concentration value")
    unit: str = Field(..., description="Standard measurement unit (e.g. µg/m³ or mg/m³ for CO)")
    observed_at_utc: datetime = Field(..., description="Original sensor reading timestamp in UTC")
    averaging_period_hours: int = Field(default=24, description="CPCB averaging window (24h or 8h)")
    coverage_hours: Optional[float] = Field(
        default=None,
        description="Hours of qualifying monitoring data in the window; None if unspecified/undocumented by source",
    )
    provider: str = Field(..., description="Data provider identifier")
    source: str = Field(..., description="Upstream source or monitoring agency (e.g. CPCB, DPCC, MPCB)")
    freshness: FreshnessType = Field(default=FreshnessType.FRESH, description="Freshness status of this individual reading")


class StationAQIResponse(BaseModel):
    """Comprehensive station report with strict provenance, availability, and freshness separation."""
    station: StationMetadata = Field(..., description="Station metadata and location")
    provenance: ProvenanceType = Field(..., description="Provenance of overall AQI (PROVIDER_REPORTED, CALCULATED, SIMULATED_DEMO, NONE)")
    availability: AvailabilityType = Field(..., description="Whether overall AQI is AVAILABLE or UNAVAILABLE")
    freshness: FreshnessType = Field(..., description="Freshness state of the observation (FRESH, STALE, EXPIRED, DEMO)")
    
    # Provider-reported vs Locally calculated AQI preservation
    provider_reported_aqi: Optional[int] = Field(
        default=None,
        description="Official scalar AQI directly published by CPCB / data.gov.in"
    )
    provider_reported_category: Optional[str] = Field(
        default=None,
        description="Official health category directly published by CPCB"
    )
    calculated_aqi: Optional[int] = Field(
        default=None,
        description="Locally computed AQI via Phase 2 CPCB NAQI engine from raw pollutants (None if Severe range)"
    )
    
    # Active Overall AQI presentation fields
    overall_aqi: Optional[int] = Field(
        default=None,
        description="Active overall AQI score (None if Severe range or UNAVAILABLE)"
    )
    overall_aqi_lower_bound: Optional[int] = Field(
        default=None,
        description="Lower bound of overall AQI: equals overall_aqi when exact, 401 when Severe"
    )
    overall_aqi_upper_bound: Optional[int] = Field(
        default=None,
        description="Upper bound of overall AQI: equals overall_aqi when exact, 500 when Severe"
    )
    is_exact: bool = Field(
        default=False,
        description="True when overall AQI is an exact scalar; False for Severe range or UNAVAILABLE"
    )
    category: str = Field(
        default="Unknown",
        description="CPCB health category (Good, Satisfactory, Moderate, Poor, Very Poor, Severe, Unknown)"
    )
    dominant_pollutant: Optional[str] = Field(
        default=None,
        description="Pollutant responsible for highest sub-index"
    )
    
    # Monitored pollutants map (keyed by pollutant name, e.g. 'PM2.5')
    pollutant_measurements: Dict[str, StationPollutantMeasurement] = Field(
        default_factory=dict,
        description="Individual measured pollutants preserved with sensor IDs and timestamps"
    )
    
    # Provenance tracking timestamps
    source: str = Field(..., description="Data provider description or agency source")
    observed_at_utc: Optional[datetime] = Field(
        default=None,
        description="Original sensor measurement time in UTC (never replaced with fetch time)"
    )
    observed_at_ist: Optional[str] = Field(
        default=None,
        description="Formatted local Indian Standard Time (Asia/Kolkata)"
    )
    fetched_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="System time when this data was fetched by SmogShield AI backend"
    )
    
    # Integrity and safety annotations
    warnings: List[str] = Field(
        default_factory=list,
        description="Safety, stale data, demo mode, or sensor coverage warnings"
    )
    unavailable_reason: Optional[str] = Field(
        default=None,
        description="Detailed explanation when overall AQI is UNAVAILABLE"
    )


class StationListResponse(BaseModel):
    """Listing response for station discovery."""
    total: int = Field(..., description="Number of discovered stations")
    stations: List[StationMetadata] = Field(..., description="List of station metadata")
    provider: str = Field(..., description="Provider used for discovery")
    demo_mode: bool = Field(..., description="Whether results are from mock demo mode")
    warnings: List[str] = Field(default_factory=list, description="Provider warnings or notes")
