"""Pydantic schemas for SmogShield AI Conversational Assistant.

Phase 6: Implementation Wave 1 - Backend Schemas & Context Assembly.

Reuses existing Phase 2-5 enums and schemas:
- Station & AQI: AvailabilityType, FreshnessType, ProvenanceType, StationAQIResponse
- Planner: CommuteMethod, HouseholdBudget, DailyPlannerRequest, DailyPlannerResponse
- Indoor: CADRUnit, IndoorAssessmentRequest, IndoorAssessmentResponse
- Transport: TransportMode, FuelType, TransportComparisonRequest, TransportComparisonResponse
- Impact: ImpactSessionSummary

Enforces:
- Strict role restriction: 'user' and 'assistant' only ('system' rejected)
- Bounded conversation history length and message size
- Timezone-aware UTC timestamps
- Explicit segregation of authoritative deterministic guidance from LLM explanation
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.indoor import CADRUnit, HouseholdBudget as IndoorHouseholdBudget
from app.schemas.planner import CommuteMethod, HouseholdBudget as PlannerHouseholdBudget
from app.schemas.transport import FuelType, TransportMode


class SupportedLanguage(str, Enum):
    """Supported conversational languages for the AI assistant."""
    en = "en"
    hi = "hi"
    hinglish = "hinglish"


class ChatRole(str, Enum):
    """Permitted client conversational roles. 'system' is strictly excluded."""
    USER = "user"
    ASSISTANT = "assistant"


class GeminiStatus(str, Enum):
    """Execution status of the generative AI layer."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE_NO_KEY = "UNAVAILABLE_NO_KEY"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    SERVICE_ERROR = "SERVICE_ERROR"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    NOT_CALLED = "NOT_CALLED"  # For Wave 1 testing/mocking prior to Wave 2 LLM execution


class ChatMessage(BaseModel):
    """An individual message in the conversation history."""
    role: ChatRole = Field(..., description="Role must be strictly 'user' or 'assistant'. 'system' is rejected.")
    content: str = Field(..., min_length=1, max_length=1000, description="Message text (max 1000 chars)")
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timezone-aware UTC timestamp")


class DeterministicAuthoritativeGuidance(BaseModel):
    """Authoritative public health recommendations computed directly by Phase 4 services.
    
    Rendered directly on frontend. Gemini explanation cannot alter or override this.
    """
    applicable_aqi_category: str
    action_priority: str
    general_population_advisory: str
    vulnerable_population_advisory: str
    schoolchildren_advisory: Optional[str] = None
    essential_travel_guidance: Optional[str] = None
    mask_protective_guidance: str
    diurnal_timing_note: Optional[str] = None
    source_citation: str = "National Centre for Disease Control (NCDC), MoHFW Health Advisory (2025)"


class GroundedCitation(BaseModel):
    """Audited citation produced by backend services."""
    source_service: str
    metric_name: str
    reported_value: str
    provenance: str     # PROVIDER_REPORTED, CALCULATED, SIMULATED_DEMO, USER_REPORTED, UNAVAILABLE
    freshness: str      # FRESH, STALE, EXPIRED, DEMO, UNKNOWN
    citation_document: str


class DailyPlannerProfileInput(BaseModel):
    """Explicit parameters for running the Phase 4 daily activity planner."""
    family_size: int = Field(default=3, ge=1, le=25)
    has_children: bool = False
    has_older_adults: bool = False
    has_sensitive_member: bool = False
    household_budget: PlannerHouseholdBudget = PlannerHouseholdBudget.medium
    commute_method: CommuteMethod = CommuteMethod.metro
    school_schedule: Optional[str] = None
    work_schedule: Optional[str] = None


class IndoorAssessmentParametersInput(BaseModel):
    """Explicit room and purifier parameters for running Phase 4 indoor assessment."""
    room_length_m: float = Field(..., gt=0, le=100)
    room_width_m: float = Field(..., gt=0, le=100)
    ceiling_height_m: float = Field(..., gt=0, le=20)
    has_air_purifier: bool = False
    cadr: Optional[float] = Field(default=None, ge=0)
    smoke_cadr: Optional[float] = Field(default=None, ge=0)
    cadr_unit: CADRUnit = CADRUnit.m3_per_hour
    filter_type: Optional[str] = None
    indoor_pollution_sources: List[str] = Field(default_factory=list)
    ventilation_available: bool = True
    household_budget: IndoorHouseholdBudget = IndoorHouseholdBudget.medium
    target_ach: Optional[float] = Field(default=None, gt=0, le=20)


class TransportComparisonParametersInput(BaseModel):
    """Explicit parameters for running Phase 5 transport comparison."""
    current_mode: TransportMode
    fuel_type: Optional[FuelType] = None
    engine_capacity_cc: Optional[int] = None
    distance_km: float = Field(..., gt=0)
    round_trip: bool = False
    occupancy: int = Field(default=1, ge=1, le=9)
    trips_per_week: int = Field(default=5, ge=1, le=14)
    alternatives: List[TransportMode] = Field(..., min_length=1)
    user_ev_kwh_per_km: Optional[float] = Field(default=None, gt=0.0)
    user_metro_kwh_per_pax_km: Optional[float] = Field(default=None, gt=0.0)


class AssistantContextInputs(BaseModel):
    """Strongly-typed input parameters for authoritative backend data fetching."""
    station_id: Optional[str] = Field(default=None, description="Station ID for live/demo AQI lookup")
    planner_profile: Optional[DailyPlannerProfileInput] = Field(default=None, description="Family profile for Phase 4 planner")
    indoor_parameters: Optional[IndoorAssessmentParametersInput] = Field(default=None, description="Room & purifier parameters for Phase 4 indoor advisor")
    transport_comparison: Optional[TransportComparisonParametersInput] = Field(default=None, description="Transport comparison parameters for Phase 5")
    include_impact_summary: bool = Field(default=False, description="Whether to include user's impact summary (requires X-Session-ID header)")
    preferred_language: SupportedLanguage = SupportedLanguage.en


class AssistantChatRequest(BaseModel):
    """Inbound request for the conversational assistant."""
    message: str = Field(..., min_length=1, max_length=1000, description="User query (max 1000 chars)")
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        max_length=6,
        description="Bounded conversation history (max 6 messages / 3 turns)"
    )
    context_inputs: AssistantContextInputs = Field(default_factory=AssistantContextInputs)

    @field_validator("conversation_history")
    def validate_conversation_history(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        if len(v) > 6:
            raise ValueError("Conversation history cannot exceed 6 messages.")
        # Validate that roles strictly alternate or follow a valid sequence
        for msg in v:
            if msg.role not in [ChatRole.USER, ChatRole.ASSISTANT]:
                raise ValueError("Only 'user' and 'assistant' roles are permitted in history.")
        return v


class AssistantChatResponse(BaseModel):
    """Outbound response isolating authoritative guidance from explanatory text."""
    authoritative_guidance: Optional[DeterministicAuthoritativeGuidance] = None
    verified_environmental_facts: Optional[Dict[str, Any]] = None
    citations: List[GroundedCitation] = Field(default_factory=list)
    gemini_status: GeminiStatus = GeminiStatus.NOT_CALLED
    gemini_explanation: str
    language: SupportedLanguage
    model_used: str
    grounding_status: str  # GROUNDED_LIVE, GROUNDED_DEMO, UNVERIFIED_STALE, DATA_UNAVAILABLE, FALLBACK_DETERMINISTIC
    disclaimer: str = Field(
        default="SmogShield AI provides explanatory assistance based on official CPCB and NCDC public health guidelines. It is not a clinical medical diagnosis or prescription."
    )
    privacy_notice: str = Field(
        default="Anonymized environmental parameters were processed. Private session tokens and personal identifiers were not transmitted."
    )


class AssistantHealthStatus(str, Enum):
    """Readiness state of the assistant service."""
    READY = "READY"
    API_KEY_MISSING = "API_KEY_MISSING"


class AssistantHealthResponse(BaseModel):
    """Passive health check response for the conversational assistant service."""
    status: AssistantHealthStatus
    configured_model: str
    api_key_configured: bool
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AssistantSmokeTestResponse(BaseModel):
    """Diagnostic response for operator-controlled smoke tests."""
    success: bool
    configured_model: str
    latency_ms: float
    diagnostic_category: str  # AUTHENTICATED_OK, RATE_LIMITED, INVALID_API_KEY, SERVICE_ERROR, TIMEOUT, NETWORK_ERROR, DISABLED
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
