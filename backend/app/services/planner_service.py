"""Personalized Daily Planner Service for SmogShield AI.

Audited and aligned with the official Government of India National Centre for
Disease Control (NCDC) Health Advisory on Air Pollution (2025).

Source:
https://ncdc.mohfw.gov.in/uploads/pdf/Enclosure%201.%20DO%20letter%20from%20Secretary%2C%20DoHFW%20to%20CS_AP%20Advisory_2025.pdf

Strictly adheres to:
- Exact 6-category NCDC 2025 guidance mapping.
- Clear separation of General Population vs Vulnerable Population advisories.
- Schoolchildren advisory: limit or postpone outdoor activities during Poor, Very Poor, and Severe conditions.
- Face masks as an optional protective choice (never mandatory, no false guarantees, fit-appropriate).
- Condition-based diurnal guidance (avoid morning/evening walks; windows 12-4 PM conditional mention).
- 12 PM - 4 PM is never called a "safe exercise window" or guaranteed lower-pollution time.
- No arbitrary health multipliers or fabricated family risk scores.
- No invented hourly forecasts.
- No medical prescriptions or clinical diagnoses.
- Structured official advisory traceability.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

from app.schemas.planner import (
    ActionPriority,
    ActivityIntensity,
    ActivityNecessity,
    ActivityPlanItem,
    ActivityType,
    CommuteMethod,
    DailyPlannerRequest,
    DailyPlannerResponse,
    HouseholdBudget,
    PlannerAQIContext,
    PlannerRecommendationItem,
    StructuredAdvisoryReference,
)
from app.schemas.station import AvailabilityType, FreshnessType, ProvenanceType, StationAQIResponse
from app.services.station_service import station_service

logger = logging.getLogger(__name__)

# Official Government of India NCDC Health Advisory on Air Pollution (2025)
NCDC_2025_ADVISORIES = {
    "Good": {
        "priority": ActionPriority.LOW,
        "general_population": "No special precautions.",
        "vulnerable_population": "No special precautions.",
        "summary": "Air quality is Good. No special precautions are recommended for general or vulnerable populations.",
    },
    "Satisfactory": {
        "priority": ActionPriority.LOW,
        "general_population": "No special precautions.",
        "vulnerable_population": "Reduce prolonged or strenuous outdoor physical exertion.",
        "summary": "Air quality is Satisfactory. General population requires no special precautions; vulnerable groups should reduce prolonged or strenuous outdoor physical exertion.",
    },
    "Moderate": {
        "priority": ActionPriority.MODERATE,
        "general_population": "Reduce prolonged or strenuous outdoor physical exertion.",
        "vulnerable_population": "Avoid prolonged or strenuous outdoor exertion.",
        "summary": "Air quality is Moderate. General population should reduce prolonged or strenuous outdoor exertion; vulnerable groups should avoid prolonged or strenuous outdoor exertion.",
    },
    "Poor": {
        "priority": ActionPriority.HIGH,
        "general_population": "Avoid outdoor physical exertion.",
        "vulnerable_population": "Avoid outdoor physical activities.",
        "summary": "Air quality is Poor. General population should avoid outdoor physical exertion; vulnerable populations should avoid outdoor physical activities.",
    },
    "Very Poor": {
        "priority": ActionPriority.URGENT,
        "general_population": "Avoid outdoor physical activities, especially morning and late evening.",
        "vulnerable_population": "Remain indoors and keep activity levels low.",
        "summary": "Air quality is Very Poor. General population should avoid outdoor physical activities (especially morning and late evening); vulnerable groups should remain indoors and keep activity levels low.",
    },
    "Severe": {
        "priority": ActionPriority.URGENT,
        "general_population": "Avoid outdoor physical activities.",
        "vulnerable_population": "Remain indoors and keep activity levels low.",
        "summary": "Air quality is Severe. General population should avoid outdoor physical activities; vulnerable populations should remain indoors and keep activity levels low.",
    },
    "Unknown": {
        "priority": ActionPriority.MODERATE,
        "general_population": "Follow general precautionary pollution-reduction practices.",
        "vulnerable_population": "Avoid unnecessary outdoor physical exposure until verified air quality is reported.",
        "summary": "Air quality data is currently unverified or unavailable. Follow baseline precautionary guidance.",
    },
}


class PlannerService:
    """Deterministic daily planner engine aligned with NCDC 2025 advisory."""

    async def generate_plan(self, request: DailyPlannerRequest) -> DailyPlannerResponse:
        """Fetch verified station data and compute deterministic NCDC 2025 recommendations."""
        # 1. Ingest verified station data via Phase 3 StationService
        raw_station_data = station_service.get_station_aqi(request.station_id)
        if hasattr(raw_station_data, "__await__"):
            station_data: StationAQIResponse = await raw_station_data
        else:
            station_data: StationAQIResponse = raw_station_data

        # 2. Extract AQI context and evaluate data conditions
        is_demo = station_data.provenance == ProvenanceType.SIMULATED_DEMO
        is_available = station_data.availability == AvailabilityType.AVAILABLE
        freshness = station_data.freshness
        category = station_data.category if is_available else "Unknown"

        aqi_ctx = PlannerAQIContext(
            overall_aqi=station_data.overall_aqi,
            overall_aqi_lower_bound=station_data.overall_aqi_lower_bound,
            overall_aqi_upper_bound=station_data.overall_aqi_upper_bound,
            is_exact=station_data.is_exact,
            category=category,
            dominant_pollutant=station_data.dominant_pollutant,
            provenance=station_data.provenance.value,
            availability=station_data.availability.value,
            freshness=station_data.freshness.value,
            observed_at_ist=station_data.observed_at_ist,
        )

        warnings: List[str] = list(station_data.warnings)
        data_limitations: List[str] = [
            "Ambient monitoring station data reflects regional outdoor air quality and does not represent an exact personal microenvironment exposure measurement.",
            "Recommendations are public-health risk mitigation advisories from NCDC (2025), not personalized medical diagnoses or clinical prescriptions.",
            "SmogShield AI does not generate synthetic hourly pollution forecasts. Fixed diurnal 'safe hours' are not declared, as meteorology, local emissions, and wind dynamically alter pollution throughout the day.",
            "Face masks are an optional protective choice and do not guarantee complete protection; they do not replace reducing unnecessary outdoor exposure.",
        ]

        structured_ref = StructuredAdvisoryReference(
            applicable_aqi_category=category,
        )

        # 3. Handle Special Data States (Unavailable, Expired, Stale, Demo)
        if not is_available or freshness == FreshnessType.EXPIRED:
            return self._build_unavailable_plan(
                request=request,
                station_data=station_data,
                aqi_ctx=aqi_ctx,
                warnings=warnings,
                data_limitations=data_limitations,
                structured_ref=structured_ref,
            )

        is_stale = freshness == FreshnessType.STALE
        if is_stale:
            warnings.append(
                "Data is STALE (> 4 hours old). Time-specific outdoor optimization cannot be reliably determined. "
                "Recommendations are indicative based on the last observed reading."
            )

        if is_demo:
            warnings.append("SIMULATED DEMO MODE: Advisory is generated using simulated demo data for testing purposes.")

        # 4. Generate Deterministic NCDC Advisories
        base_advisory = NCDC_2025_ADVISORIES.get(category, NCDC_2025_ADVISORIES["Unknown"])
        action_priority = base_advisory["priority"]
        general_pop_adv = base_advisory["general_population"]
        vulnerable_pop_adv = base_advisory["vulnerable_population"]
        public_health_summary = base_advisory["summary"]

        # Conditional Timing Guidance (NCDC 2025: on Poor-to-Severe days)
        conditional_timing: Optional[Dict[str, str]] = None
        if category in ["Poor", "Very Poor", "Severe"] and not is_stale:
            conditional_timing = {
                "outdoor_walks": (
                    "Avoid outdoor morning and late-evening walks when winter temperature inversions "
                    "and calm winds trap particulate matter near ground level."
                ),
                "windows_and_doors": (
                    "Keep external doors and windows closed during morning and late evening hours to limit outdoor smog entry."
                ),
                "ventilation_window_note": (
                    "If household natural ventilation is necessary, NCDC advisory notes the 12 PM to 4 PM afternoon period. "
                    "Note: This is general public-health guidance, not a guarantee of safe outdoor air and not an endorsement of afternoon outdoor exercise."
                ),
            }
        elif is_stale and category in ["Poor", "Very Poor", "Severe"]:
            conditional_timing = {
                "stale_timing_disclaimer": "Time-specific optimization is withheld because current station data is stale (> 4 hours old)."
            }

        recommendations: List[PlannerRecommendationItem] = []

        # Determine activities to evaluate
        activities_to_eval = request.planned_activities
        if not activities_to_eval:
            activities_to_eval = self._get_default_activities(request)

        for item in activities_to_eval:
            rec = self._evaluate_activity(
                item=item,
                category=category,
                request=request,
            )
            recommendations.append(rec)

        # Commute-specific advisory
        commute_rec = self._evaluate_commute(
            method=request.commute_method,
            category=category,
            request=request,
        )
        recommendations.append(commute_rec)

        # Vulnerable family members advisories
        if request.has_children:
            child_rec = self._evaluate_children_advisory(category=category, request=request)
            recommendations.append(child_rec)

        if request.has_older_adults:
            senior_rec = self._evaluate_older_adults_advisory(category=category, request=request)
            recommendations.append(senior_rec)

        if request.has_sensitive_member:
            sens_rec = self._evaluate_sensitive_member_advisory(category=category, request=request)
            recommendations.append(sens_rec)

        # General non-pharmacological household practices
        general_practices = self._get_general_household_practices(category=category, budget=request.household_budget)

        return DailyPlannerResponse(
            generated_at=datetime.now(timezone.utc),
            station_id=station_data.station.station_id,
            station_name=station_data.station.station_name,
            city=station_data.station.city,
            aqi_context=aqi_ctx,
            action_priority=action_priority,
            public_health_summary=public_health_summary,
            general_population_advisory=general_pop_adv,
            vulnerable_population_advisory=vulnerable_pop_adv,
            conditional_timing_guidance=conditional_timing,
            recommendations=recommendations,
            general_household_practices=general_practices,
            structured_advisory_reference=structured_ref,
            evidence_source="National Centre for Disease Control (NCDC), MoHFW Health Advisory on Air Pollution (2025)",
            data_limitations=data_limitations,
            warnings=warnings,
        )

    def _get_default_activities(self, request: DailyPlannerRequest) -> List[ActivityPlanItem]:
        """Generate default routine activities based on household profile."""
        items: List[ActivityPlanItem] = []
        if request.has_children:
            items.append(
                ActivityPlanItem(
                    activity_type=ActivityType.school_commute,
                    intensity=ActivityIntensity.low,
                    necessity=ActivityNecessity.essential,
                    scheduled_time=request.school_schedule or "Morning & Afternoon",
                )
            )
            items.append(
                ActivityPlanItem(
                    activity_type=ActivityType.outdoor_play,
                    intensity=ActivityIntensity.high,
                    necessity=ActivityNecessity.discretionary,
                    scheduled_time="Evening",
                )
            )

        if request.commute_method != CommuteMethod.work_from_home:
            items.append(
                ActivityPlanItem(
                    activity_type=ActivityType.work_commute,
                    intensity=ActivityIntensity.low,
                    necessity=ActivityNecessity.essential,
                    scheduled_time=request.work_schedule or "Regular Working Hours",
                )
            )

        items.append(
            ActivityPlanItem(
                activity_type=ActivityType.outdoor_exercise,
                intensity=request.activity_intensity or ActivityIntensity.moderate,
                necessity=request.activity_necessity or ActivityNecessity.optional,
            )
        )
        return items

    def _evaluate_activity(
        self,
        item: ActivityPlanItem,
        category: str,
        request: DailyPlannerRequest,
    ) -> PlannerRecommendationItem:
        """Deterministic evaluation of activity against NCDC 2025 recommendations."""
        act_name = item.activity_type.value.replace("_", " ").title()
        is_essential = item.necessity == ActivityNecessity.essential
        is_vulnerable = request.has_children or request.has_older_adults or request.has_sensitive_member

        if category in ["Good", "Satisfactory"]:
            if category == "Satisfactory" and is_vulnerable and item.intensity == ActivityIntensity.high:
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Reduce Prolonged Strenuous Exertion",
                    recommendation=f"Vulnerable members should reduce prolonged or strenuous outdoor physical exertion during {act_name.lower()}.",
                    reason="NCDC (2025) advisory recommends vulnerable populations reduce prolonged strenuous exertion in Satisfactory conditions.",
                    alternative_activity="Light indoor movement or pacing.",
                    target_group="Vulnerable Household Members",
                    practical_steps=[
                        "Take rest breaks if fatigue occurs.",
                        "Stay hydrated.",
                    ],
                )
            return PlannerRecommendationItem(
                activity_type=item.activity_type.value,
                action="Proceed with Ordinary Awareness",
                recommendation=f"{act_name} can proceed normally with ordinary awareness.",
                reason="NCDC (2025) advisory notes no special precautions are required for the general population in this category.",
                alternative_activity="Standard outdoor or indoor activities.",
                target_group="General Population",
                practical_steps=["Maintain normal daily routine and hydration."],
            )

        elif category == "Moderate":
            if is_vulnerable:
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Avoid Prolonged or Strenuous Exertion",
                    recommendation=f"Vulnerable individuals should avoid prolonged or strenuous outdoor physical exertion during {act_name.lower()}.",
                    reason="NCDC (2025) advisory recommends avoiding prolonged or strenuous outdoor exertion for vulnerable groups in Moderate air.",
                    alternative_activity="Light indoor physical activities, stretching, or reading.",
                    target_group="Vulnerable Population (Children, Seniors, Sensitive)",
                    practical_steps=[
                        "Relocate strenuous physical activities indoors.",
                        "Take frequent rest breaks during necessary outdoor movement.",
                    ],
                )
            else:
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Reduce Prolonged Strenuous Exertion",
                    recommendation=f"Reduce prolonged or strenuous outdoor physical exertion during {act_name.lower()}.",
                    reason="NCDC (2025) advisory recommends general population reduce prolonged or strenuous outdoor exertion in Moderate air.",
                    alternative_activity="Moderate indoor exercise or gym.",
                    target_group="General Population",
                    practical_steps=["Pace exertion and avoid heavily congested traffic roads."],
                )

        elif category == "Poor":
            # Essential travel is exempted from avoidance; check necessity first regardless of vulnerability.
            if is_essential:
                mask_guidance = (
                    "Consider using a properly fitted disposable N95/N99 mask for short essential transit. "
                    "Masks are optional and do not guarantee complete protection."
                )
                practical = [
                    "Reduce outdoor waiting time where possible.",
                    "If available, use public transit, school bus, metro, or carpool to limit exposure.",
                    mask_guidance,
                ]
                if item.activity_type == ActivityType.school_commute:
                    recommendation_text = (
                        "Proceed with school commute as essential travel. "
                        "Show current AQI and provenance, reduce waiting time, and consider bus or carpool. "
                        + mask_guidance
                    )
                else:
                    recommendation_text = (
                        "Proceed with essential travel. "
                        "Show current AQI and provenance, reduce waiting time, and consider alternative transit. "
                        + mask_guidance
                    )
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Essential Travel Guidance",
                    recommendation=recommendation_text,
                    reason="NCDC (2025) advisory permits essential travel but recommends exposure-minimization in Poor air quality.",
                    alternative_activity="Use indoor alternatives where feasible or choose lower-exposure transit.",
                    target_group="All (essential travelers)",
                    practical_steps=practical,
                )
            # Discretionary activities: vulnerability determines guidance level.
            elif is_vulnerable:
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Avoid Outdoor Physical Activities",
                    recommendation=f"Vulnerable household members should avoid outdoor physical activities for {act_name.lower()}.",
                    reason="NCDC (2025) advisory explicitly recommends vulnerable populations avoid outdoor physical activities when air is Poor.",
                    alternative_activity="Indoor games, home study, or quiet indoor play.",
                    target_group="Vulnerable Population",
                    practical_steps=[
                        "Keep activities indoors in a closed room.",
                        "If outdoor transit is essential, disposable N95 masks may provide optional short-term protection if correctly fitted.",
                    ],
                )
            else:
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Avoid Outdoor Physical Exertion",
                    recommendation=f"General population should avoid outdoor physical exertion during {act_name.lower()}.",
                    reason="NCDC (2025) advisory recommends general population avoid outdoor physical exertion in Poor air.",
                    alternative_activity="Indoor workout, home tasks, or digital errand completion.",
                    target_group="General Population",
                    practical_steps=[
                        "Avoid strenuous outdoor jogging, running, or heavy physical labour.",
                        "For short essential transit, disposable N95/N99 masks are an optional protective choice when fitted properly.",
                    ],
                )

        elif category in ["Very Poor", "Severe"]:
            # Essential activities: provide exposure-minimisation guidance; do NOT cancel.
            if is_essential:
                mask_guidance = (
                    "Consider using a properly fitted disposable N95/N99 mask for the shortest possible outdoor transit. "
                    "Masks are optional and do not guarantee complete protection."
                )
                practical = [
                    "Minimise total outdoor time as much as possible.",
                    "If available, use enclosed public transit (metro, school bus) or carpool to reduce direct exposure.",
                    mask_guidance,
                    "Avoid outdoor waiting in open air; wait indoors until departure time where possible.",
                ]
                if item.activity_type == ActivityType.school_commute:
                    recommendation_text = (
                        "Proceed with school commute as essential travel. "
                        "Strictly minimise outdoor waiting time; prefer enclosed school bus or carpool. "
                        + mask_guidance
                    )
                else:
                    recommendation_text = (
                        "Proceed with essential travel using the shortest outdoor route. "
                        "Strictly minimise outdoor exposure; prefer enclosed transit alternatives. "
                        + mask_guidance
                    )
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Essential Travel — Minimise Outdoor Exposure",
                    recommendation=recommendation_text,
                    reason=(
                        "NCDC (2025) advisory recommends avoiding outdoor physical activities in Very Poor and Severe air. "
                        "Essential travel is exempted but must be conducted with strict exposure minimisation."
                    ),
                    alternative_activity="Postpone if possible; otherwise use the most enclosed, lowest-exposure route available.",
                    target_group="All (essential travelers)",
                    practical_steps=practical,
                )
            # Discretionary activities: advise avoidance / remain indoors.
            if is_vulnerable:
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Remain Indoors & Keep Activity Low",
                    recommendation="Vulnerable members should remain indoors and keep activity levels low.",
                    reason="NCDC (2025) advisory recommends vulnerable populations remain indoors and keep activity levels low in Very Poor and Severe bands.",
                    alternative_activity="Restful indoor activities in a closed room.",
                    target_group="Vulnerable Population (Children, Seniors, Sensitive)",
                    practical_steps=[
                        "Keep doors and windows firmly closed.",
                        "Avoid any vigorous indoor or outdoor exercise.",
                    ],
                )
            else:
                return PlannerRecommendationItem(
                    activity_type=item.activity_type.value,
                    action="Avoid Outdoor Physical Activities",
                    recommendation="Avoid outdoor physical activities, especially during morning and late evening hours.",
                    reason="NCDC (2025) advisory recommends general population avoid outdoor physical activities in Very Poor and Severe air.",
                    alternative_activity="Indoor home tasks or telecommuting.",
                    target_group="General Population",
                    practical_steps=[
                        "Strictly minimize outdoor exposure duration.",
                        "If transit is unavoidable, a correctly fitted disposable N95/N99 mask is an optional protective choice per manufacturer instructions.",
                    ],
                )

        return PlannerRecommendationItem(
            activity_type=item.activity_type.value,
            action="General Precaution",
            recommendation=f"Exercise general awareness during {act_name.lower()}.",
            reason="Air quality data is unverified or unavailable.",
            alternative_activity="Indoor routine.",
            target_group="All",
            practical_steps=["Maintain basic hygiene and follow public local updates."],
        )

    def _evaluate_commute(
        self,
        method: CommuteMethod,
        category: str,
        request: DailyPlannerRequest,
    ) -> PlannerRecommendationItem:
        """Deterministic commute guidance aligned with NCDC 2025."""
        method_name = method.value.replace("_", " ").title()

        if method == CommuteMethod.work_from_home:
            return PlannerRecommendationItem(
                activity_type="commute_advisory",
                action="Work From Home Active",
                recommendation="Remote work eliminates outdoor commute travel during elevated pollution.",
                reason="Avoiding outdoor transit during smog episodes aligns with NCDC exposure minimization recommendations.",
                alternative_activity="N/A (already remote).",
                target_group="Working Adults",
                practical_steps=["Maintain clean indoor air in the home workstation."],
            )

        if category in ["Poor", "Very Poor", "Severe"]:
            mask_guidance = (
                "For short essential transit, a disposable N95/N99 mask is an optional protective choice "
                "when fitted correctly according to manufacturer's instructions. Note that masks do not guarantee complete protection "
                "and do not replace reducing unnecessary outdoor travel."
            )

            if method in [CommuteMethod.walk, CommuteMethod.bicycle, CommuteMethod.two_wheeler, CommuteMethod.auto_rickshaw]:
                return PlannerRecommendationItem(
                    activity_type="commute_advisory",
                    action="Commute Advisory - Outdoor Road Transit",
                    recommendation=f"Commuting via {method_name} involves direct outdoor air exposure. Minimize exposure duration.",
                    reason="Outdoor physical movement during Poor-to-Severe pollution exposes commuters to ambient particulate matter.",
                    alternative_activity="Consider public metro transit or carpooling where available.",
                    target_group="Daily Commuters",
                    practical_steps=[
                        mask_guidance,
                        "Avoid stopping directly behind heavy exhaust plumes at traffic signals.",
                    ],
                )
            elif method in [CommuteMethod.car_ac, CommuteMethod.carpool]:
                return PlannerRecommendationItem(
                    activity_type="commute_advisory",
                    action="Vehicle Cabin - Set Recirculation Mode",
                    recommendation="Keep vehicle windows rolled up and switch air conditioning to cabin recirculation mode.",
                    reason="Recirculation reduces drawing contaminated roadway air directly into the passenger cabin.",
                    alternative_activity="Metro rail where feasible.",
                    target_group="Car Commuters",
                    practical_steps=[
                        "Switch vehicle ventilation to inside air recirculation.",
                        "Inspect cabin air filter per vehicle manufacturer maintenance schedule.",
                    ],
                )
            else:  # Bus or Metro
                return PlannerRecommendationItem(
                    activity_type="commute_advisory",
                    action="Public Transit Commute",
                    recommendation=f"For {method_name} travel, minimize wait times in open-air transit stops.",
                    reason="Enclosed rail transit cabins provide physical separation from surface vehicle exhaust.",
                    alternative_activity="Metro rail is preferred over open-road travel.",
                    target_group="Public Transit Users",
                    practical_steps=[
                        mask_guidance,
                        "Keep bus windows closed during transit through congested corridors.",
                    ],
                )
        else:
            return PlannerRecommendationItem(
                activity_type="commute_advisory",
                action="Standard Commute Routine",
                recommendation=f"Commute via {method_name} can proceed normally with standard awareness.",
                reason="Current air quality meets acceptable national benchmarks for daily travel.",
                alternative_activity="Standard transit.",
                target_group="Daily Commuters",
                practical_steps=["Follow standard road safety practices."],
            )

    def _evaluate_children_advisory(self, category: str, request: DailyPlannerRequest) -> PlannerRecommendationItem:
        """Schoolchildren advisory aligned with NCDC 2025 school guidelines."""
        if category in ["Poor", "Very Poor", "Severe"]:
            return PlannerRecommendationItem(
                activity_type="child_health_protection",
                action="Limit or Postpone Outdoor School Activities",
                recommendation=(
                    "Per NCDC (2025) school advisory, schools are recommended to limit or postpone "
                    "outdoor school activities, sports, physical education, and outdoor assemblies during Poor, Very Poor, or Severe air."
                ),
                reason="NCDC (2025) air pollution health advisory recommends postponing outdoor physical activities in schools during elevated pollution.",
                alternative_activity="Indoor classroom learning, drawing, board games, or reading.",
                target_group="School-age Children",
                practical_steps=[
                    "Advise school administration to shift physical training (PT) and sports sessions indoors.",
                    "Ensure adequate hydration throughout the school day.",
                    "If masks are considered for short school commutes, ensure they are age-appropriate and fit comfortably without causing breathing resistance; masks are an optional choice.",
                ],
            )
        else:
            return PlannerRecommendationItem(
                activity_type="child_health_protection",
                action="Normal School Activities",
                recommendation="School activities, sports, and outdoor play can proceed normally with standard care.",
                reason="Air quality meets acceptable standards for childhood outdoor activity.",
                alternative_activity="Standard school sports and outdoor play.",
                target_group="School-age Children",
                practical_steps=["Ensure adequate hydration and sun protection."],
            )

    def _evaluate_older_adults_advisory(self, category: str, request: DailyPlannerRequest) -> PlannerRecommendationItem:
        """Older adults advisory aligned with NCDC 2025."""
        if category in ["Poor", "Very Poor", "Severe"]:
            return PlannerRecommendationItem(
                activity_type="senior_citizen_protection",
                action="Remain Indoors & Avoid Morning/Evening Outdoor Walks",
                recommendation="Remain indoors, keep activity levels low, and avoid outdoor morning and late-evening walks.",
                reason="NCDC (2025) advisory advises vulnerable populations to remain indoors and avoid morning/late-evening outdoor walks.",
                alternative_activity="Gentle indoor walking inside hallways or light indoor stretching in a closed room.",
                target_group="Older Adults & Seniors",
                practical_steps=[
                    "Avoid outdoor exercise during early morning and late evening hours.",
                    "Keep living areas closed to outdoor air during high pollution episodes.",
                ],
            )
        elif category in ["Satisfactory", "Moderate"]:
            return PlannerRecommendationItem(
                activity_type="senior_citizen_protection",
                action="Reduce Prolonged or Strenuous Outdoor Exertion",
                recommendation="Reduce prolonged or strenuous outdoor physical exertion; avoid intense exertion in Moderate air.",
                reason="NCDC (2025) advisory advises vulnerable groups to reduce or avoid strenuous outdoor exertion in Satisfactory to Moderate air.",
                alternative_activity="Light outdoor or indoor walking with frequent rest periods.",
                target_group="Older Adults & Seniors",
                practical_steps=["Take regular rest breaks and stay comfortably warm in winter."],
            )
        else:
            return PlannerRecommendationItem(
                activity_type="senior_citizen_protection",
                action="Normal Walk Routine",
                recommendation="Older adults may proceed with regular daily activities with ordinary awareness.",
                reason="Air quality is Good.",
                alternative_activity="Outdoor walk in parks.",
                target_group="Older Adults & Seniors",
                practical_steps=["Maintain comfortable physical routine."],
            )

    def _evaluate_sensitive_member_advisory(self, category: str, request: DailyPlannerRequest) -> PlannerRecommendationItem:
        """Sensitive member advisory aligned with NCDC 2025."""
        if category in ["Poor", "Very Poor", "Severe"]:
            return PlannerRecommendationItem(
                activity_type="sensitive_member_protocol",
                action="Remain Indoors & Avoid Outdoor Activities",
                recommendation=(
                    "Sensitive household members should remain indoors and avoid outdoor physical activities. "
                    "Keep doctor-prescribed routine maintenance medication or inhalers accessible as directed by your physician."
                ),
                reason="NCDC (2025) advisory recommends individuals with pre-existing cardiopulmonary conditions remain indoors and keep activity levels low.",
                alternative_activity="Restful indoor tasks in a clean indoor space.",
                target_group="Sensitive Household Members",
                practical_steps=[
                    "Keep prescribed maintenance medications and inhalers readily accessible as advised by your healthcare provider.",
                    "Avoid indoor irritants like incense smoke, mosquito coils, and strong cooking fumes.",
                    "Consult your physician promptly if experiencing unusual respiratory discomfort or chest tightness.",
                ],
            )
        elif category in ["Satisfactory", "Moderate"]:
            return PlannerRecommendationItem(
                activity_type="sensitive_member_protocol",
                action="Reduce or Avoid Strenuous Outdoor Exertion",
                recommendation="Reduce prolonged outdoor exertion in Satisfactory air; avoid strenuous outdoor exertion in Moderate air.",
                reason="NCDC (2025) advisory advises vulnerable individuals to reduce or avoid strenuous exertion in Satisfactory and Moderate conditions.",
                alternative_activity="Light indoor activity.",
                target_group="Sensitive Household Members",
                practical_steps=[
                    "Take frequent rest periods.",
                    "Follow individual care plans established with your physician.",
                ],
            )
        else:
            return PlannerRecommendationItem(
                activity_type="sensitive_member_protocol",
                action="Standard Awareness",
                recommendation="Normal routine with standard personal awareness.",
                reason="Air quality is Good.",
                alternative_activity="Standard activities.",
                target_group="Sensitive Household Members",
                practical_steps=["Continue following standard physician guidance."],
            )

    def _get_general_household_practices(self, category: str, budget: HouseholdBudget) -> List[str]:
        """Affordable non-pharmacological household air quality management practices."""
        practices = [
            "Use damp mopping (wet cloth wiping) instead of dry sweeping with brooms to prevent resuspending settled fine dust into indoor air.",
            "Avoid burning agarbatti (incense sticks), dhoop, candles, or mosquito coils inside closed rooms.",
            "Operate an appropriately installed and externally vented kitchen exhaust or chimney during cooking to exhaust combustion particles.",
        ]

        if category in ["Poor", "Very Poor", "Severe"]:
            practices.extend([
                "Keep exterior doors and windows closed, especially during morning and late evening hours, to limit outdoor smog entry.",
                "Place rolled damp towels or foam strips along gaps at the bottom of exterior doors to reduce outdoor particulate infiltration.",
            ])

        if budget == HouseholdBudget.low:
            practices.append(
                "Prioritize zero-cost source control (stopping incense/coils and wet mopping) over purchasing expensive unverified gadgets."
            )
        elif budget == HouseholdBudget.high:
            practices.append(
                "Consider deploying an appropriately sized mechanical True HEPA air purifier, following manufacturer operating and filter maintenance instructions."
            )

        return practices

    def _build_unavailable_plan(
        self,
        request: DailyPlannerRequest,
        station_data: StationAQIResponse,
        aqi_ctx: PlannerAQIContext,
        warnings: List[str],
        data_limitations: List[str],
        structured_ref: StructuredAdvisoryReference,
    ) -> DailyPlannerResponse:
        """Build a safe baseline response when AQI is unavailable or expired."""
        reason = station_data.unavailable_reason or "Station monitoring data is unavailable or expired."
        warnings.append(f"AQI-DEPENDENT SCHEDULING UNAVAILABLE: {reason}")

        return DailyPlannerResponse(
            generated_at=datetime.now(timezone.utc),
            station_id=station_data.station.station_id,
            station_name=station_data.station.station_name,
            city=station_data.station.city,
            aqi_context=aqi_ctx,
            action_priority=ActionPriority.MODERATE,
            public_health_summary=(
                "Air quality data is currently UNAVAILABLE or EXPIRED for this monitoring station. "
                "Because verified ambient readings cannot be confirmed, specific AQI-dependent outdoor scheduling "
                "is suspended. Follow standard precautionary household pollution-reduction measures."
            ),
            general_population_advisory="Follow general precautionary pollution-reduction practices.",
            vulnerable_population_advisory="Avoid unnecessary outdoor physical exposure until verified air quality is reported.",
            conditional_timing_guidance=None,
            recommendations=[
                PlannerRecommendationItem(
                    activity_type="baseline_precaution",
                    action="Exercise General Precaution",
                    recommendation="Proceed with daily schedule exercising sensible general precautions until fresh verified data is reported.",
                    reason="Unverified or absent air quality monitoring data prevents reliable exposure risk determination.",
                    alternative_activity="Prefer well-ventilated indoor spaces with clean indoor air.",
                    target_group="All Family Members",
                    practical_steps=[
                        "Monitor official municipal updates for verified air quality reporting.",
                        "If stepping outdoors in visible haze, a disposable N95 mask is an optional protective choice.",
                    ],
                )
            ],
            general_household_practices=self._get_general_household_practices(
                category="Unknown", budget=request.household_budget
            ),
            structured_advisory_reference=structured_ref,
            data_limitations=data_limitations,
            warnings=warnings,
        )


# Global service singleton instance
planner_service = PlannerService()
