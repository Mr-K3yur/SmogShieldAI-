from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PollutantMeasurement(BaseModel):
    """Raw pollutant measurement with explicit metadata and data capture duration."""
    pollutant: str = Field(..., description="Pollutant name (e.g. PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb)")
    value: float = Field(..., description="Measured concentration value")
    unit: str = Field(..., description="Measurement unit (e.g. µg/m³ or mg/m³ for CO)")
    averaging_hours: int = Field(default=24, description="Standard averaging window (24h or 8h)")
    hours_recorded: float = Field(default=24.0, description="Actual recorded monitoring duration in hours")
    recorded_at: Optional[datetime] = Field(default=None, description="Timestamp of sensor measurement")


class PollutantSubIndex(BaseModel):
    """Evaluated sub-index for an individual pollutant.

    For categories Good through Very Poor, sub_index is an exact interpolated
    integer (0-400) and is_exact is True.

    For the Severe category, the official CPCB breakpoint table does not define
    an upper concentration boundary, so exact linear interpolation is impossible.
    In this case: sub_index is None, sub_index_lower_bound is 401,
    sub_index_upper_bound is 500, and is_exact is False.
    """
    pollutant: str = Field(..., description="Pollutant identifier")
    concentration: float = Field(..., description="Evaluated concentration")
    unit: str = Field(..., description="Measurement unit")
    averaging_hours: int = Field(..., description="Standard averaging window")
    hours_recorded: float = Field(..., description="Recorded monitoring hours")
    sub_index: Optional[int] = Field(
        default=None,
        description="Exact CPCB sub-index (0-400) when determinable; None for Severe or invalid",
    )
    sub_index_lower_bound: Optional[int] = Field(
        default=None,
        description="Lower bound of sub-index range: equals sub_index when exact, 401 for Severe",
    )
    sub_index_upper_bound: Optional[int] = Field(
        default=None,
        description="Upper bound of sub-index range: equals sub_index when exact, 500 for Severe",
    )
    is_exact: bool = Field(
        default=False,
        description="True when sub_index is an exact interpolated value (Good-Very Poor); False for Severe or invalid",
    )
    category: str = Field(default="Unknown", description="CPCB category (Good to Severe)")
    is_valid: bool = Field(default=True, description="Whether measurement satisfies all CPCB criteria")
    validation_error: Optional[str] = Field(default=None, description="Reason if calculation was rejected")
    note: Optional[str] = Field(
        default=None,
        description=(
            "Explanatory note, e.g., when a Severe sub-index is reported as a "
            "range (401-500) because the official CPCB table does not define "
            "an upper breakpoint for linear interpolation."
        ),
    )


class OverallAQIResult(BaseModel):
    """Overall Station AQI following official CPCB methodology and data rules.

    When the dominant pollutant is in the Severe range, overall_aqi is None
    because the exact value is not determinable. Use overall_aqi_lower_bound
    and overall_aqi_upper_bound for the range, and is_exact to distinguish.

    When all sub-indices are exact (Good-Very Poor), overall_aqi is the exact
    maximum sub-index and is_exact is True.
    """
    overall_aqi: Optional[int] = Field(
        default=None,
        description="Exact overall AQI score when determinable; None when dominant is Severe or data insufficient",
    )
    overall_aqi_lower_bound: Optional[int] = Field(
        default=None,
        description="Lower bound: equals overall_aqi when exact, 401 when dominant is Severe",
    )
    overall_aqi_upper_bound: Optional[int] = Field(
        default=None,
        description="Upper bound: equals overall_aqi when exact, 500 when dominant is Severe",
    )
    is_exact: bool = Field(
        default=False,
        description="True when overall_aqi is exact; False when dominant is Severe or data insufficient",
    )
    category: str = Field(default="Unknown", description="Overall health category")
    dominant_pollutant: Optional[str] = Field(default=None, description="Primary driver of the index")
    status: str = Field(default="UNAVAILABLE", description="CALCULATED | UNAVAILABLE")
    reason: str = Field(..., description="Detailed status or explanation")
    eligible_for_overall_aqi: bool = Field(..., description="Whether CPCB minimum criteria are met")
    valid_pollutants_count: int = Field(..., description="Number of valid pollutant sub-indices")
    has_mandatory_pm: bool = Field(..., description="Whether PM2.5 or PM10 requirement is fulfilled")
    sub_indices: Dict[str, PollutantSubIndex] = Field(
        default_factory=dict, description="All evaluated pollutant sub-indices"
    )
    timestamp_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Calculation timestamp in UTC",
    )


class AQICalculationRequest(BaseModel):
    """Payload to compute CPCB AQI from a set of raw measurements."""
    measurements: List[PollutantMeasurement] = Field(..., description="List of monitored pollutant readings")


class AQICalculationResponse(BaseModel):
    """API response envelope for CPCB AQI calculation."""
    result: OverallAQIResult
