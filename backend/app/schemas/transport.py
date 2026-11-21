"""Pydantic schemas for Sustainable Transportation & Environmental Impact Tracker.

Covers:
- Standardized transport modes, fuel types, and vehicle categories
- Emission factor registry schemas
- Transportation comparison request and response models
- Mode-specific occupancy validation
- Strict engine capacity boundaries
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from app.schemas.planner import HouseholdBudget
from app.schemas.station import StationAQIResponse


class TransportMode(str, Enum):
    """Standardized transportation modes."""
    petrol_motorcycle = "petrol_motorcycle"
    petrol_car = "petrol_car"
    diesel_car = "diesel_car"
    cng_auto = "cng_auto"
    intracity_bus = "intracity_bus"
    metro = "metro"
    carpool = "carpool"
    electric_vehicle = "electric_vehicle"
    walking = "walking"
    cycling = "cycling"


class FuelType(str, Enum):
    """Vehicle fuel types."""
    petrol = "petrol"
    diesel = "diesel"
    cng = "cng"
    electric = "electric"
    none = "none"


class FactorVerificationStatus(str, Enum):
    """Audit status of emission factor in registry."""
    VERIFIED_CURRENT = "VERIFIED_CURRENT"
    HISTORICAL_PROVISIONAL = "HISTORICAL_PROVISIONAL"
    UNAVAILABLE = "UNAVAILABLE"


class EmissionFactorEntry(BaseModel):
    """An individual audited emission factor entry in the registry."""
    factor_id: str = Field(..., description="Unique factor identifier")
    mode: str = Field(..., description="Transport mode or domain description")
    fuel_type: Optional[str] = Field(default=None, description="Applicable fuel type")
    engine_capacity_boundary: Optional[str] = Field(default=None, description="Strict engine displacement boundary (e.g. '< 125 cc')")
    base_value: Optional[float] = Field(default=None, description="Un-uplifted base test-cycle factor value")
    uplift_pct: Optional[float] = Field(default=None, description="Percentage uplift applied for real-world driving")
    default_value: float = Field(..., description="Active default emission factor value")
    unit: str = Field(..., description="Standard measurement unit (e.g. kg CO2/veh-km, kg CO2/pax-km, kg CO2/kWh)")
    is_default_for_calc: bool = Field(default=True, description="Whether this factor is the active default in calculations")
    verification_status: FactorVerificationStatus = Field(..., description="Audit status")
    source_name: str = Field(..., description="Publishing organization")
    document_title: str = Field(..., description="Official publication title")
    publication_year: int = Field(..., description="Year of publication")
    publication_date: Optional[str] = Field(default=None, description="Month/Year of publication")
    applicable_fiscal_year: Optional[str] = Field(default=None, description="Fiscal year of underlying data")
    source_page: Optional[str] = Field(default=None, description="Page or section citation in document")
    geography: str = Field(default="India", description="Applicable geographic scope")
    calculation_scope: str = Field(default="Tailpipe CO2", description="Emissions scope (CO2 only, not CO2e)")
    limitations: str = Field(..., description="Documented limitations, boundaries, and exclusions")
    methodology_notes: Optional[str] = Field(default=None, description="Methodology details or reporting caveats")


class EmissionFactorRegistryResponse(BaseModel):
    """Response payload for reading the audited emission factor registry."""
    total_factors: int = Field(..., description="Total factors registered (exactly 9)")
    retrieved_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    factors: List[EmissionFactorEntry] = Field(..., description="List of emission factor entries")
    registry_notes: List[str] = Field(default_factory=list, description="General registry disclaimers and scope notes")


class TransportModeResult(BaseModel):
    """Deterministic emission calculation for an individual transport mode."""
    mode: TransportMode = Field(..., description="Transport mode evaluated")
    is_available: bool = Field(..., description="Whether a verified emission calculation is available")
    unavailable_reason: Optional[str] = Field(default=None, description="Reason if calculation is unavailable")
    factor_id_used: Optional[str] = Field(default=None, description="Registry factor ID applied")
    factor_value: Optional[float] = Field(default=None, description="Factor value applied")
    factor_unit: Optional[str] = Field(default=None, description="Unit of the factor")
    factor_status: Optional[FactorVerificationStatus] = Field(default=None, description="Verification status")
    effective_distance_km: float = Field(..., description="Distance evaluated (doubled if round-trip)")
    occupancy: int = Field(default=1, description="Total persons in vehicle including driver")
    total_vehicle_emissions_kg_co2: Optional[float] = Field(default=None, description="Total vehicle tailpipe CO2")
    passenger_emissions_kg_co2: Optional[float] = Field(default=None, description="Per-passenger tailpipe CO2")
    is_user_guided: bool = Field(default=False, description="Whether calculation relies on user-supplied energy data")
    user_guided_source_note: Optional[str] = Field(default=None, description="Note explaining user-supplied energy assumptions")
    health_guidance_note: Optional[str] = Field(default=None, description="NCDC 2025 air quality health advisory for this mode")
    is_recommended_for_commute: bool = Field(default=True, description="False if outdoor exertion is contraindicated by AQI")
    lifecycle_disclosure: Optional[str] = Field(default=None, description="Disclosure on excluded lifecycle emissions")
    calculation_trace: List[str] = Field(default_factory=list, description="Step-by-step arithmetic trace")


class AvoidedEmissionsComparison(BaseModel):
    """Comparison of alternative mode against baseline."""
    alternative_mode: TransportMode
    baseline_passenger_emissions_kg_co2: float
    alternative_passenger_emissions_kg_co2: Optional[float]
    avoided_kg_co2_per_trip: Optional[float] = Field(
        default=None,
        description="Baseline minus alternative. Positive = reduction; Negative = emissions increase"
    )
    is_emissions_increase: bool = Field(default=False, description="True if alternative produces more emissions than baseline")
    projected_weekly_saving_kg_co2: Optional[float] = Field(default=None, description="Projected weekly savings based on frequency")
    projected_monthly_saving_kg_co2: Optional[float] = Field(default=None, description="Projected monthly savings (weekly * 4.33)")
    comparison_summary: str = Field(..., description="Clear human-readable summary of the comparison")


class TransportComparisonRequest(BaseModel):
    """Request payload to compare transport modes with AQI integration."""
    station_id: str = Field(..., description="Selected monitoring station identifier for AQI context")
    current_mode: TransportMode = Field(..., description="Current baseline travel mode")
    fuel_type: Optional[FuelType] = Field(default=None, description="Fuel type for baseline private vehicle")
    engine_capacity_cc: Optional[int] = Field(default=None, description="Exact engine capacity in cc")
    distance_km: float = Field(..., gt=0.0, description="One-way trip distance in km")
    round_trip: bool = Field(default=False, description="Whether the trip is round-trip")
    occupancy: int = Field(default=1, ge=1, le=9, description="Total people in vehicle including driver")
    trips_per_week: int = Field(default=5, ge=1, le=14, description="Weekly trip frequency for forward projections")
    alternatives: List[TransportMode] = Field(..., min_length=1, description="Alternative modes to evaluate")
    user_cost_current_inr: Optional[float] = Field(default=None, ge=0.0, description="Optional user-entered travel cost in INR")
    household_budget: HouseholdBudget = Field(default=HouseholdBudget.medium, description="Household budget tier")
    has_children: bool = Field(default=False)
    has_older_adults: bool = Field(default=False)
    has_sensitive_member: bool = Field(default=False)
    user_ev_kwh_per_km: Optional[float] = Field(default=None, gt=0.0, description="Optional rated energy consumption for EV")
    user_metro_kwh_per_pax_km: Optional[float] = Field(default=None, gt=0.0, description="Optional metro specific energy consumption")

    @model_validator(mode="after")
    def validate_mode_occupancy(self) -> "TransportComparisonRequest":
        if self.current_mode == TransportMode.cng_auto and self.occupancy > 3:
            raise ValueError("CNG auto maximum occupancy is 3 (including driver).")
        if self.current_mode in [TransportMode.petrol_car, TransportMode.diesel_car, TransportMode.carpool] and self.occupancy > 9:
            raise ValueError("Car maximum occupancy is 9.")
        return self


class TransportComparisonResponse(BaseModel):
    """Comprehensive comparison response with AQI context and non-invention disclaimers."""
    generated_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    station_id: str
    station_name: str
    city: str
    current_aqi: Optional[int]
    aqi_category: str
    ncdc_general_advisory: str
    ncdc_vulnerable_advisory: str
    effective_distance_km: float
    round_trip: bool
    baseline_result: TransportModeResult
    alternative_results: List[TransportModeResult]
    avoided_comparisons: List[AvoidedEmissionsComparison]
    disclaimers: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
