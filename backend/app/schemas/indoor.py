"""Pydantic schemas for Indoor Air Quality Advisor and Purifier Sizing Engine.

Audited and aligned with evidence-based physics calculations and safety standards:
- Room Volume = Length × Width × Ceiling Height.
- CADR conversion: 1 CFM = 1.699 m³/hour.
- Estimated ACH = CADR / Room Volume.
- No automatic adequacy labels (e.g. >=4 adequate, <2.5 undersized removed).
- Target ACH is strictly optional; comparison only performed if explicitly supplied by user.
- Manufacturer-specific maintenance guidance (no generic unsupported intervals).
- User-reported filter types flagged as self-reported and unverified.
- Kitchen ventilation safety with combustion appliance depressurization/backdraft warning.
- Debunks houseplant air-cleaning myths for PM2.5.
- Never claims exact indoor AQI without real calibrated sensors.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CADRUnit(str, Enum):
    """Clean Air Delivery Rate (CADR) measurement units."""
    m3_per_hour = "m3/h"
    cfm = "CFM"


class HouseholdBudget(str, Enum):
    """Household budget tier."""
    low = "low"
    medium = "medium"
    high = "high"


class RoomDimensions(BaseModel):
    """Room geometrical dimensions."""
    length_m: float = Field(..., gt=0, le=100, description="Room length in metres")
    width_m: float = Field(..., gt=0, le=100, description="Room width in metres")
    height_m: float = Field(..., gt=0, le=20, description="Ceiling height in metres")


class IndoorAssessmentRequest(BaseModel):
    """Request payload for indoor air quality and purifier sizing assessment."""
    station_id: Optional[str] = Field(
        default=None,
        description="Optional monitoring station identifier for outdoor air quality context",
    )
    room_length_m: float = Field(..., gt=0, le=100, description="Room length in metres (must be positive)")
    room_width_m: float = Field(..., gt=0, le=100, description="Room width in metres (must be positive)")
    ceiling_height_m: float = Field(..., gt=0, le=20, description="Ceiling height in metres (must be positive)")
    has_air_purifier: bool = Field(default=False, description="Whether an air purifier is available in the room")
    cadr: Optional[float] = Field(
        default=None,
        ge=0,
        description="Manufacturer-declared Clean Air Delivery Rate (CADR); null if unknown",
    )
    smoke_cadr: Optional[float] = Field(
        default=None,
        ge=0,
        description="Manufacturer-declared Smoke CADR specifically for fine particles (PM2.5), if provided",
    )
    cadr_unit: CADRUnit = Field(
        default=CADRUnit.m3_per_hour,
        description="CADR measurement unit (m3/h or CFM)",
    )
    filter_type: Optional[str] = Field(
        default=None,
        description="User-reported filter type (e.g. HEPA H13, Activated Carbon, Pre-filter, Unknown)",
    )
    indoor_pollution_sources: List[str] = Field(
        default_factory=list,
        description="Reported indoor particulate sources (e.g. agarbatti, mosquito_coils, unvented_cooking, smoking)",
    )
    ventilation_available: bool = Field(
        default=True,
        description="Whether operable windows or mechanical ventilation vents exist",
    )
    household_budget: HouseholdBudget = Field(
        default=HouseholdBudget.medium,
        description="Household budget tier for recommendations",
    )
    target_ach: Optional[float] = Field(
        default=None,
        gt=0,
        le=20,
        description="Optional user-selected target Air Changes per Hour for sizing calculation. Never automatically assumed.",
    )


class FiltrationAssessment(BaseModel):
    """Assessment of mechanical particle filtration in the space without universal medical adequacy thresholds."""
    purifier_status: str = Field(..., description="Status (PURIFIER_PRESENT, PURIFIER_ABSENT, UNSPECIFIED_CADR)")
    target_comparison: Optional[str] = Field(
        default=None,
        description="Comparison against user-specified target ACH, if provided by user; None if no target specified",
    )
    is_user_reported_filter: bool = Field(
        default=True,
        description="Filter type is user self-reported, not independently laboratory verified",
    )
    explanation: str = Field(..., description="Technical explanation of theoretical CADR and estimated ACH")
    guidance: List[str] = Field(
        default_factory=list,
        description="Manufacturer-specific maintenance and operational guidance",
    )


class IndoorActionItem(BaseModel):
    """Actionable recommendation for indoor pollution source control."""
    source: str = Field(..., description="Identified pollution source or risk")
    action: str = Field(..., description="Recommended mitigation step")
    priority: str = Field(..., description="Priority level (HIGH, MEDIUM, LOW)")
    reason: str = Field(..., description="Scientific explanation of particulate or VOC generation")


class VentilationAdvisory(BaseModel):
    """Condition-based ventilation guidance based on verified outdoor air."""
    outdoor_aqi_category: Optional[str] = Field(default=None, description="Current outdoor CPCB category if available")
    strategy: str = Field(..., description="Ventilation strategy (e.g. Restrict Infiltration, Controlled Flush, Cross-Ventilate)")
    guidance: str = Field(..., description="Detailed ventilation recommendation")
    precautions: List[str] = Field(default_factory=list, description="Safety precautions (safety vents, flues, backdraft, etc.)")


class IndoorAssessmentResponse(BaseModel):
    """Complete indoor air quality assessment response."""
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when assessment was generated in UTC",
    )
    room_dimensions: RoomDimensions = Field(..., description="Evaluated room dimensions")
    room_volume_m3: float = Field(..., description="Calculated room volume in cubic metres")
    available_cadr_m3h: Optional[float] = Field(default=None, description="Available CADR normalized to m³/hour")
    available_cadr_cfm: Optional[float] = Field(default=None, description="Available CADR converted to CFM")
    calculated_ach: Optional[float] = Field(
        default=None,
        description="Theoretical estimated Air Changes per Hour (ACH = CADR / Volume); null if CADR unavailable",
    )
    target_ach: Optional[float] = Field(
        default=None,
        description="User-selected target ACH calculation assumption; None if not provided",
    )
    required_cadr_m3h: Optional[float] = Field(
        default=None,
        description="Required CADR in m³/h to achieve user-selected target ACH; None if no target provided",
    )
    required_cadr_cfm: Optional[float] = Field(
        default=None,
        description="Required CADR in CFM to achieve user-selected target ACH; None if no target provided",
    )
    filtration_assessment: FiltrationAssessment = Field(..., description="Mechanical filtration sizing assessment")
    source_control_recommendations: List[IndoorActionItem] = Field(
        default_factory=list,
        description="Prioritized indoor pollution source control steps",
    )
    ventilation_recommendations: VentilationAdvisory = Field(
        ...,
        description="Condition-based ventilation advice tied to outdoor conditions",
    )
    affordable_interventions: List[str] = Field(
        default_factory=list,
        description="Affordable, practical household interventions tailored to budget",
    )
    formula_and_assumptions: Dict[str, str] = Field(
        default_factory=dict,
        description="Formulas, conversion factors, and calculation assumptions",
    )
    data_source_and_limitations: List[str] = Field(
        default_factory=list,
        description="Transparency notes regarding indoor sensors, plant myths, and assumptions",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Safety warnings (ozone-generating devices, safety vents, kitchen exhaust backdraft)",
    )
