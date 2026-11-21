"""Pydantic schemas for Personalized Daily Planner.

Audited and aligned with the official Government of India National Centre for
Disease Control (NCDC) Health Advisory on Air Pollution (2025).

Enforces:
- Exact 6-category NCDC 2025 guidance mapping.
- Clear separation of General Population vs Vulnerable Population advisories.
- Schoolchildren outdoor postponement/limitation for Poor, Very Poor, and Severe bands.
- Optional protective masking guidance (no mandatory claims, no false guarantees).
- Conditional diurnal timing guidance (avoid morning/evening walks, windows 12-4 PM conditional note).
- Structured advisory traceability to NCDC 2025 official document.
- Zero arbitrary health multipliers, zero fabricated risk scores, zero clinical prescriptions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HouseholdBudget(str, Enum):
    """Household budget tier."""
    low = "low"
    medium = "medium"
    high = "high"


class CommuteMethod(str, Enum):
    """Primary commuting mode for work/school."""
    walk = "walk"
    bicycle = "bicycle"
    two_wheeler = "two_wheeler"
    auto_rickshaw = "auto_rickshaw"
    bus = "bus"
    metro = "metro"
    car_non_ac = "car_non_ac"
    car_ac = "car_ac"
    carpool = "carpool"
    work_from_home = "work_from_home"


class ActivityType(str, Enum):
    """Standardized activity types for daily scheduling."""
    school_commute = "school_commute"
    work_commute = "work_commute"
    outdoor_exercise = "outdoor_exercise"
    outdoor_play = "outdoor_play"
    outdoor_sports = "outdoor_sports"
    shopping_errands = "shopping_errands"
    essential_travel = "essential_travel"
    essential_medical_travel = "essential_medical_travel"
    indoor_activities = "indoor_activities"


class ActivityIntensity(str, Enum):
    """Exertion level of the activity."""
    low = "low"
    moderate = "moderate"
    high = "high"


class ActivityNecessity(str, Enum):
    """Necessity level of the activity."""
    essential = "essential"
    discretionary = "discretionary"
    optional = "optional"


class ActionPriority(str, Enum):
    """Overall action priority for household awareness."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ActivityPlanItem(BaseModel):
    """An individual planned daily activity item."""
    activity_type: ActivityType = Field(..., description="Type of daily activity")
    intensity: ActivityIntensity = Field(default=ActivityIntensity.moderate, description="Exertion level")
    necessity: ActivityNecessity = Field(default=ActivityNecessity.essential, description="Necessity level")
    scheduled_time: Optional[str] = Field(default=None, description="Optional user schedule note (e.g. '07:30 - 08:30')")
    notes: Optional[str] = Field(default=None, description="Optional user notes")


class DailyPlannerRequest(BaseModel):
    """Request payload for generating a deterministic daily planner."""
    station_id: str = Field(..., description="Selected monitoring station identifier")
    family_size: int = Field(default=3, ge=1, le=25, description="Number of family members in household")
    has_children: bool = Field(default=False, description="Whether school-age or young children are present")
    has_older_adults: bool = Field(default=False, description="Whether elderly or older adults are present")
    has_sensitive_member: bool = Field(
        default=False,
        description="Optional flag indicating household member with respiratory, cardiac, or general sensitivity",
    )
    household_budget: HouseholdBudget = Field(default=HouseholdBudget.medium, description="Household budget tier")
    commute_method: CommuteMethod = Field(default=CommuteMethod.metro, description="Primary commute mode")
    school_schedule: Optional[str] = Field(default=None, description="Optional school schedule window or description")
    work_schedule: Optional[str] = Field(default=None, description="Optional work schedule window or description")
    planned_activities: List[ActivityPlanItem] = Field(
        default_factory=list,
        description="List of specific planned activities. If empty, default routine activities are evaluated.",
    )
    activity_intensity: Optional[ActivityIntensity] = Field(
        default=ActivityIntensity.moderate,
        description="Default activity intensity if not specified per item",
    )
    activity_necessity: Optional[ActivityNecessity] = Field(
        default=ActivityNecessity.essential,
        description="Default activity necessity if not specified per item",
    )
    preferred_language: str = Field(default="en", description="Preferred output language (e.g. 'en', 'hi')")


class PlannerAQIContext(BaseModel):
    """Verified AQI context from Phase 3 station service."""
    overall_aqi: Optional[int] = Field(default=None, description="Overall scalar AQI (None if Severe or UNAVAILABLE)")
    overall_aqi_lower_bound: Optional[int] = Field(default=None, description="Lower bound of AQI range")
    overall_aqi_upper_bound: Optional[int] = Field(default=None, description="Upper bound of AQI range")
    is_exact: bool = Field(default=False, description="Whether AQI is an exact scalar")
    category: str = Field(default="Unknown", description="CPCB health category")
    dominant_pollutant: Optional[str] = Field(default=None, description="Pollutant responsible for highest sub-index")
    provenance: str = Field(..., description="Data provenance (PROVIDER_REPORTED, CALCULATED, SIMULATED_DEMO, NONE)")
    availability: str = Field(..., description="Availability status (AVAILABLE, UNAVAILABLE)")
    freshness: str = Field(..., description="Freshness status (FRESH, STALE, EXPIRED, DEMO)")
    observed_at_ist: Optional[str] = Field(default=None, description="Observation timestamp in IST")


class PlannerRecommendationItem(BaseModel):
    """A deterministic recommendation for a specific activity or demographic group."""
    activity_type: str = Field(..., description="Activity identifier or group")
    action: str = Field(..., description="Recommended action summary (e.g. Proceed Normally, Postpone, Shift Indoors)")
    recommendation: str = Field(..., description="Detailed practical recommendation")
    reason: str = Field(..., description="Scientific and contextual reason based on AQI and family profile")
    alternative_activity: str = Field(..., description="Practical, lower-exposure indoor or modified alternative")
    target_group: str = Field(..., description="Target family demographic (e.g. Children, Daily Commuters, All)")
    practical_steps: List[str] = Field(default_factory=list, description="Actionable protective measures")


class StructuredAdvisoryReference(BaseModel):
    """Full authoritative traceability metadata for the health advisory."""
    issuing_organization: str = Field(
        default="National Centre for Disease Control (NCDC), Directorate General of Health Services, Ministry of Health and Family Welfare (MoHFW), Government of India"
    )
    document_title: str = Field(default="Health Advisory on Air Pollution (2025)")
    publication_year: str = Field(default="2025")
    applicable_aqi_category: str = Field(..., description="Air quality category for this reference")
    relevant_section: str = Field(default="Advisory on Air Pollution for General and Vulnerable Populations")
    public_source_url: str = Field(
        default="https://ncdc.mohfw.gov.in/uploads/pdf/Enclosure%201.%20DO%20letter%20from%20Secretary%2C%20DoHFW%20to%20CS_AP%20Advisory_2025.pdf"
    )


class DailyPlannerResponse(BaseModel):
    """Complete personalized daily planner response."""
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when plan was generated in UTC",
    )
    station_id: str = Field(..., description="Monitoring station identifier")
    station_name: str = Field(..., description="Human-readable station name")
    city: str = Field(..., description="Station city")
    aqi_context: PlannerAQIContext = Field(..., description="Verified AQI context")
    action_priority: ActionPriority = Field(..., description="Overall household action priority")
    public_health_summary: str = Field(..., description="NCDC 2025 public health summary for this air quality band")
    general_population_advisory: str = Field(
        ...,
        description="Explicit official NCDC 2025 advisory for the general population",
    )
    vulnerable_population_advisory: str = Field(
        ...,
        description="Explicit official NCDC 2025 advisory for vulnerable populations (children, elderly, sensitive members)",
    )
    conditional_timing_guidance: Optional[Dict[str, str]] = Field(
        default=None,
        description="Condition-based diurnal timing advisory based on NCDC 2025 guidelines",
    )
    recommendations: List[PlannerRecommendationItem] = Field(
        default_factory=list,
        description="Personalized activity and demographic recommendations",
    )
    general_household_practices: List[str] = Field(
        default_factory=list,
        description="General non-pharmacological household air quality management practices",
    )
    structured_advisory_reference: StructuredAdvisoryReference = Field(
        ...,
        description="Structured official source traceability to NCDC 2025 health advisory",
    )
    evidence_source: str = Field(
        default="National Centre for Disease Control (NCDC), MoHFW Health Advisory on Air Pollution (2025)",
        description="Authoritative public health reference",
    )
    data_limitations: List[str] = Field(
        default_factory=list,
        description="Transparency notes on forecasts, sensor duration, and personal exposure limits",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Safety, stale data, demo mode, or sensor coverage warnings",
    )
