"""Pydantic schemas for Impact Tracker and Session Management.

Enforces:
- 100% server-side emission calculations (zero trusted client emissions inputs)
- Explicit baseline scenario requirement for actual avoided emissions
- Server-issued session tokens and private session isolation
- Strict mode-specific occupancy limits
- Mandatory in-memory temporary storage disclosures
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from app.schemas.transport import FuelType, TransportMode


STORAGE_DISCLAIMER_TEXT = (
    "Trip history is stored in temporary server memory only and is not persisted. "
    "Data will be lost when the server restarts or the session expires after 24 hours of inactivity. "
    "In-memory session tracking requires a single server process; multi-worker deployment requires shared external storage."
)


class BaselineTripInput(BaseModel):
    """Documented baseline commute scenario for calculating actual avoided emissions."""
    mode: TransportMode = Field(..., description="Baseline mode that was replaced")
    fuel_type: Optional[FuelType] = Field(default=None, description="Fuel type of baseline vehicle")
    engine_capacity_cc: Optional[int] = Field(default=None, description="Exact engine capacity in cc")
    occupancy: int = Field(default=1, ge=1, le=9, description="Total persons including driver")
    user_ev_kwh_per_km: Optional[float] = Field(default=None, gt=0.0)
    user_metro_kwh_per_pax_km: Optional[float] = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def validate_baseline_occupancy(self) -> "BaselineTripInput":
        if self.mode == TransportMode.cng_auto and self.occupancy > 3:
            raise ValueError("CNG auto maximum occupancy is 3 (including driver).")
        if self.mode in [TransportMode.petrol_car, TransportMode.diesel_car, TransportMode.carpool] and self.occupancy > 9:
            raise ValueError("Car maximum occupancy is 9.")
        return self


class TripLogEntry(BaseModel):
    """Client input payload for recording a completed trip.
    
    Zero client emissions values accepted. Calculated 100% on server.
    """
    mode: TransportMode = Field(..., description="Completed transport mode")
    fuel_type: Optional[FuelType] = Field(default=None, description="Fuel type if private vehicle")
    engine_capacity_cc: Optional[int] = Field(default=None, description="Exact engine capacity in cc")
    distance_km: float = Field(..., gt=0.0, description="One-way trip distance in km")
    round_trip: bool = Field(default=False, description="Whether trip was round-trip")
    occupancy: int = Field(default=1, ge=1, le=9, description="Total people in vehicle including driver")
    baseline_scenario: Optional[BaselineTripInput] = Field(
        default=None,
        description="Optional baseline commute mode replaced by this trip; required to compute actual avoided emissions"
    )
    user_ev_kwh_per_km: Optional[float] = Field(default=None, gt=0.0)
    user_metro_kwh_per_pax_km: Optional[float] = Field(default=None, gt=0.0)
    station_id: Optional[str] = Field(default=None, description="Optional station ID to fetch verified server-side AQI context")
    user_reported_aqi_category: Optional[str] = Field(
        default=None,
        description="Optional user-reported AQI category (labelled as unverified user-reported)"
    )
    notes: Optional[str] = Field(default=None, description="Optional user notes")

    @model_validator(mode="after")
    def validate_trip_occupancy(self) -> "TripLogEntry":
        if self.mode == TransportMode.cng_auto and self.occupancy > 3:
            raise ValueError("CNG auto maximum occupancy is 3 (including driver).")
        if self.mode in [TransportMode.petrol_car, TransportMode.diesel_car, TransportMode.carpool] and self.occupancy > 9:
            raise ValueError("Car maximum occupancy is 9.")
        return self


class CompletedTripRecord(BaseModel):
    """Server-audited completed trip record stored in memory."""
    trip_id: str = Field(..., description="Unique trip UUID")
    idempotency_key: str = Field(..., description="Client idempotency key used for this operation")
    logged_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: TransportMode
    effective_distance_km: float
    round_trip: bool
    occupancy: int
    passenger_emissions_kg_co2: float = Field(..., description="Deterministic server-calculated passenger tailpipe CO2")
    factor_id_used: str = Field(..., description="Audited factor ID applied")
    factor_status: str = Field(..., description="Status of factor used")
    baseline_mode: Optional[TransportMode] = None
    baseline_passenger_emissions_kg_co2: Optional[float] = None
    actual_avoided_kg_co2: Optional[float] = Field(
        default=None,
        description="Actual avoided emissions (None if no baseline scenario was provided)"
    )
    avoided_status: str = Field(..., description="AVOIDED_CALCULATED, BASELINE_NOT_PROVIDED, or EMISSIONS_INCREASE")
    avoided_explanation: str
    aqi_context_source: str = Field(default="NONE", description="SERVER_VERIFIED, USER_REPORTED, or NONE")
    aqi_category: Optional[str] = None
    notes: Optional[str] = None


class SessionCreationResponse(BaseModel):
    """Response payload for newly created in-memory session."""
    session_id: str = Field(..., description="Server-issued UUID4 session bearer token")
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at_utc: datetime
    storage_disclaimer: str = Field(default=STORAGE_DISCLAIMER_TEXT)


class TripLogResult(BaseModel):
    """Response returned upon logging a completed trip."""
    session_id: str
    trip: CompletedTripRecord
    storage_disclaimer: str = Field(default=STORAGE_DISCLAIMER_TEXT)
    message: str


class WeeklyActualSummary(BaseModel):
    """Summary of completed trips grouped by ISO week."""
    iso_year: int
    iso_week: int
    trip_count: int
    total_passenger_emissions_kg_co2: float
    total_avoided_kg_co2: float
    emissions_increase_trips: int


class MonthlyActualSummary(BaseModel):
    """Summary of completed trips grouped by calendar month."""
    year: int
    month: int
    trip_count: int
    total_passenger_emissions_kg_co2: float
    total_avoided_kg_co2: float
    emissions_increase_trips: int


class ImpactSessionSummary(BaseModel):
    """Comprehensive impact session summary strictly separating actual from projected figures."""
    session_id: str
    created_at_utc: datetime
    last_accessed_at_utc: datetime
    expires_at_utc: datetime
    storage_disclaimer: str = Field(default=STORAGE_DISCLAIMER_TEXT)
    completed_action_count: int = Field(..., description="Count of actual completed trips logged")
    actual_total_emissions_kg_co2: float = Field(..., description="Sum of passenger emissions from completed trips")
    actual_avoided_kg_co2: float = Field(..., description="Sum of verified avoided emissions from completed trips with baselines")
    trips_without_baseline_count: int = Field(..., description="Count of completed trips where baseline was not provided")
    emissions_by_mode: Dict[str, float] = Field(default_factory=dict, description="Passenger CO2 broken down by mode")
    weekly_summaries: List[WeeklyActualSummary] = Field(default_factory=list, description="Actual ISO week summaries (never multiplied by 4.33)")
    monthly_summaries: List[MonthlyActualSummary] = Field(default_factory=list, description="Actual calendar month summaries (never extrapolated)")
    completed_trips: List[CompletedTripRecord] = Field(default_factory=list, description="All completed trip records in this session")
