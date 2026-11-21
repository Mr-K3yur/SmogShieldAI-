"""Indoor Air Quality Advisor and Purifier Sizing Service for SmogShield AI.

Audited and aligned with physics-based calculations and safety standards:
- Room Volume = Length × Width × Ceiling Height.
- CADR conversion: 1 CFM = 1.699 m³/hour.
- Estimated ACH = CADR / Room Volume.
- No automatic adequacy labels (e.g. >=4 adequate, <2.5 undersized removed).
- Target ACH is strictly optional; compared only when explicitly provided by user.
- Without a user target, returns numerical estimated ACH without safety/adequacy labels.
- Explains that actual air cleaning depends on fan speed, filter condition, room leakage, placement, and air mixing.
- Purifier maintenance directs users to follow manufacturer instructions (no generic intervals).
- Filter type flagged as user self-reported, not independently verified.
- Kitchen ventilation recommends externally vented range hoods and warns of combustion appliance depressurization/backdraft risks.
- Debunks houseplant air-cleaning claims for PM2.5.
- Never claims exact indoor AQI without real calibrated sensors.
- Never provides unverified DIY electrical purifier assembly instructions.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional

from app.schemas.indoor import (
    CADRUnit,
    FiltrationAssessment,
    HouseholdBudget,
    IndoorActionItem,
    IndoorAssessmentRequest,
    IndoorAssessmentResponse,
    RoomDimensions,
    VentilationAdvisory,
)
from app.schemas.station import AvailabilityType, StationAQIResponse
from app.services.station_service import station_service

logger = logging.getLogger(__name__)

CFM_TO_M3H = 1.699


class IndoorAirService:
    """Deterministic indoor air quality and purifier sizing engine."""

    async def assess_room(self, request: IndoorAssessmentRequest) -> IndoorAssessmentResponse:
        """Calculate geometrical room volume, evaluate CADR/ACH, and generate recommendations."""
        # 1. Geometry Calculations
        length = round(request.room_length_m, 2)
        width = round(request.room_width_m, 2)
        height = round(request.ceiling_height_m, 2)
        volume_m3 = round(length * width * height, 2)

        # 2. CADR and ACH Evaluation (use smoke_cadr if provided, otherwise general cadr)
        active_cadr = request.smoke_cadr if request.smoke_cadr is not None and request.smoke_cadr > 0 else request.cadr

        available_cadr_m3h: Optional[float] = None
        available_cadr_cfm: Optional[float] = None
        calculated_ach: Optional[float] = None

        if request.has_air_purifier and active_cadr is not None and active_cadr > 0:
            if request.cadr_unit == CADRUnit.cfm:
                available_cadr_cfm = round(active_cadr, 2)
                available_cadr_m3h = round(active_cadr * CFM_TO_M3H, 2)
            else:  # m3/h
                available_cadr_m3h = round(active_cadr, 2)
                available_cadr_cfm = round(active_cadr / CFM_TO_M3H, 2)

            calculated_ach = round(available_cadr_m3h / volume_m3, 2)

        # 3. Target CADR Calculations (only if user explicitly provided target_ach)
        required_cadr_m3h: Optional[float] = None
        required_cadr_cfm: Optional[float] = None
        target_ach = request.target_ach

        if target_ach is not None and target_ach > 0:
            required_cadr_m3h = round(volume_m3 * target_ach, 2)
            required_cadr_cfm = round(required_cadr_m3h / CFM_TO_M3H, 2)

        # 4. Outdoor Air Context (if station_id provided)
        outdoor_category: Optional[str] = None
        if request.station_id:
            try:
                raw_station_resp = station_service.get_station_aqi(request.station_id)
                if hasattr(raw_station_resp, "__await__"):
                    station_resp: StationAQIResponse = await raw_station_resp
                else:
                    station_resp: StationAQIResponse = raw_station_resp

                if station_resp.availability == AvailabilityType.AVAILABLE:
                    outdoor_category = station_resp.category
            except Exception as e:
                logger.warning(f"Could not fetch outdoor station {request.station_id}: {str(e)}")

        # 5. Build Sub-components
        filtration_assessment = self._evaluate_filtration(
            has_purifier=request.has_air_purifier,
            cadr_m3h=available_cadr_m3h,
            ach=calculated_ach,
            volume_m3=volume_m3,
            filter_type=request.filter_type,
            target_ach=target_ach,
            has_smoke_cadr=request.smoke_cadr is not None,
        )

        source_controls = self._evaluate_source_controls(
            sources=request.indoor_pollution_sources,
            budget=request.household_budget,
            outdoor_category=outdoor_category,
        )

        ventilation_advisory = self._evaluate_ventilation(
            outdoor_category=outdoor_category,
            ventilation_available=request.ventilation_available,
        )

        affordable_interventions = self._get_affordable_interventions(
            budget=request.household_budget,
            has_purifier=request.has_air_purifier,
        )

        # 6. Safety Warnings & Scientific Reality Disclosures
        warnings: List[str] = [
            "OZONE SAFETY WARNING: Strictly avoid air purifiers that produce ozone, negative ions without zero-ozone verification, or unverified photocatalytic oxidation (PCO). Ozone is a respiratory irritant.",
            "SAFETY VENT PRECAUTION: Never block mandatory combustion ventilation, kitchen safety vents, or water heater (geyser) flues when sealing rooms against smog.",
            "KITCHEN EXHAUST BACKDRAFT SAFETY: Exhaust-only systems can depressurize living spaces and create backdraft risks with open-flue combustion appliances if adequate replacement air is absent. Follow appliance manufacturer installation guidance.",
            "ELECTRICAL SAFETY: SmogShield AI does not provide unverified DIY electrical purifier assembly instructions due to fire and electrical safety risks.",
        ]

        data_limitations: List[str] = [
            "SmogShield AI does not claim to know exact indoor AQI without real-time, calibrated indoor particulate sensors.",
            "HOUSEPLANT REALITY CHECK: While indoor plants provide aesthetic value, peer-reviewed environmental research demonstrates that potted house plants do not effectively remove fine particulate matter (PM2.5) or VOCs at rates relevant to residential room ventilation. They cannot substitute for mechanical particle filtration.",
            "Theoretical estimated ACH is a physics-based calculation from room volume and declared CADR. Actual clean air delivery depends on operating fan speed, filter condition, room air leakage, unit placement, and room air mixing.",
            "Target ACH is a user-selected calculation assumption, not a universal medical recommendation or guaranteed safe-air threshold.",
        ]

        formula_assumptions: Dict[str, str] = {
            "room_volume_formula": "Volume (m³) = Length (m) × Width (m) × Ceiling Height (m)",
            "cadr_conversion_factor": "1 CFM = 1.699 m³/hour",
            "ach_formula": "Estimated ACH = Available CADR (m³/h) / Room Volume (m³)",
            "required_cadr_formula": "Required CADR (m³/h) = Room Volume (m³) × User Target ACH",
            "target_ach_note": "A target ACH is evaluated only when explicitly provided by the user. It is not an automatically assigned health standard.",
        }

        return IndoorAssessmentResponse(
            generated_at=datetime.now(timezone.utc),
            room_dimensions=RoomDimensions(length_m=length, width_m=width, height_m=height),
            room_volume_m3=volume_m3,
            available_cadr_m3h=available_cadr_m3h,
            available_cadr_cfm=available_cadr_cfm,
            calculated_ach=calculated_ach,
            target_ach=target_ach,
            required_cadr_m3h=required_cadr_m3h,
            required_cadr_cfm=required_cadr_cfm,
            filtration_assessment=filtration_assessment,
            source_control_recommendations=source_controls,
            ventilation_recommendations=ventilation_advisory,
            affordable_interventions=affordable_interventions,
            formula_and_assumptions=formula_assumptions,
            data_source_and_limitations=data_limitations,
            warnings=warnings,
        )

    def _evaluate_filtration(
        self,
        has_purifier: bool,
        cadr_m3h: Optional[float],
        ach: Optional[float],
        volume_m3: float,
        filter_type: Optional[str],
        target_ach: Optional[float],
        has_smoke_cadr: bool,
    ) -> FiltrationAssessment:
        """Deterministic assessment of mechanical filtration without arbitrary adequacy labels."""
        if not has_purifier:
            return FiltrationAssessment(
                purifier_status="PURIFIER_ABSENT",
                target_comparison=None,
                is_user_reported_filter=False,
                explanation=(
                    f"No mechanical air purifier is reported in this room ({volume_m3} m³). "
                    "Mechanical particle filtration (such as True HEPA) is the established method for removing "
                    "airborne fine particulate matter (PM2.5) from indoor air."
                ),
                guidance=[
                    "Focus on indoor source control (avoiding incense, coils, unvented frying, and tobacco smoke).",
                    "Keep exterior windows and doors closed during elevated outdoor pollution periods.",
                    "If considering an air purifier, verify that manufacturer-tested CADR matches room volume and follows certified standards.",
                ],
            )

        if cadr_m3h is None or ach is None:
            return FiltrationAssessment(
                purifier_status="UNSPECIFIED_CADR",
                target_comparison=None,
                is_user_reported_filter=bool(filter_type),
                explanation=(
                    "An air purifier is reported, but manufacturer Clean Air Delivery Rate (CADR) was not specified. "
                    "Theoretical ACH cannot be calculated without manufacturer CADR data."
                ),
                guidance=[
                    "Check the product manual or manufacturer label for Clean Air Delivery Rate (CADR in m³/h or CFM) or Smoke CADR.",
                    "Follow manufacturer instructions for pre-filter maintenance and filter replacement intervals.",
                    "Filter type is self-reported by user and has not been independently verified.",
                ],
            )

        # CADR and ACH are available
        cadr_type_note = "Smoke CADR" if has_smoke_cadr else "CADR"
        filter_desc = f" (Self-reported filter: {filter_type})" if filter_type else ""

        # Target comparison: only if user provided target_ach
        target_comp: Optional[str] = None
        if target_ach is not None:
            if ach >= target_ach:
                target_comp = f"Estimated theoretical ACH ({ach:.1f}) meets or exceeds your selected target of {target_ach:.1f} ACH."
            else:
                target_comp = f"Estimated theoretical ACH ({ach:.1f}) is below your selected target of {target_ach:.1f} ACH."

        explanation = (
            f"Based on declared {cadr_type_note} ({cadr_m3h:.1f} m³/h) and room volume ({volume_m3} m³), "
            f"the theoretical estimated air exchange rate is {ach:.1f} Air Changes per Hour (ACH){filter_desc}. "
            "Actual clean air delivery in practice depends on operational fan speed, filter condition, "
            "room air leakage, placement, and room air mixing."
        )

        guidance = [
            "Follow the manufacturer's specific user manual for filter cleaning and replacement schedules.",
            "Do not wash or vacuum filters unless explicitly permitted in the manufacturer's instructions.",
            "Ensure purifier air intake and exhaust are not obstructed by furniture, walls, or curtains.",
            "Filter type is self-reported by user and has not been independently laboratory verified.",
        ]

        return FiltrationAssessment(
            purifier_status="PURIFIER_PRESENT",
            target_comparison=target_comp,
            is_user_reported_filter=bool(filter_type),
            explanation=explanation,
            guidance=guidance,
        )

    def _evaluate_source_controls(
        self,
        sources: List[str],
        budget: HouseholdBudget,
        outdoor_category: Optional[str],
    ) -> List[IndoorActionItem]:
        """Prioritized indoor source control recommendations with combustion safety."""
        items: List[IndoorActionItem] = []
        normalized_sources = [s.lower().strip() for s in sources]

        # Incense / Agarbatti / Dhoop
        if any(s in normalized_sources for s in ["agarbatti", "agarbatti_incense", "incense", "dhoop"]):
            items.append(
                IndoorActionItem(
                    source="Incense & Agarbatti Burning",
                    action="Cease burning agarbatti, dhoop, and scented candles inside residential rooms.",
                    priority="HIGH",
                    reason=(
                        "Burning incense generates concentrated indoor spikes of fine particulate matter (PM2.5) "
                        "and volatile combustion byproducts in closed spaces."
                    ),
                )
            )

        # Mosquito Coils
        if any(s in normalized_sources for s in ["mosquito_coils", "mosquito_coil", "coils"]):
            items.append(
                IndoorActionItem(
                    source="Mosquito Coils",
                    action="Replace burning mosquito coils with physical window mesh screens, bed nets, or non-combustion alternatives.",
                    priority="HIGH",
                    reason=(
                        "Burning mosquito coils emits significant fine particulate matter (PM2.5) and organic pollutants "
                        "directly into breathing zones."
                    ),
                )
            )

        # Kitchen Cooking / Frying
        if any(s in normalized_sources for s in ["unvented_cooking", "cooking", "frying"]):
            is_high_smog = outdoor_category in ["Poor", "Very Poor", "Severe"]
            smog_note = " When outdoor pollution is high, balance source capture with keeping living room windows closed." if is_high_smog else ""
            items.append(
                IndoorActionItem(
                    source="Kitchen Cooking & Frying",
                    action="Use an appropriately installed and externally vented range hood or kitchen exhaust where available; cover pans during frying.",
                    priority="HIGH",
                    reason=(
                        "High-heat frying and unvented gas cooking release fine aerosols and combustion byproducts."
                        f"{smog_note} Note: Ensure combustion appliances have adequate make-up air to avoid depressurization backdraft risks."
                    ),
                )
            )

        # Tobacco / Smoking
        if any(s in normalized_sources for s in ["smoking", "tobacco", "cigarettes", "bidi"]):
            items.append(
                IndoorActionItem(
                    source="Indoor Tobacco & Bidi Smoking",
                    action="Strictly prohibit all indoor smoking.",
                    priority="HIGH",
                    reason=(
                        "Environmental tobacco smoke is a primary indoor contributor to particulate matter and toxic combustion byproducts."
                    ),
                )
            )

        # Dust Sweeping
        if any(s in normalized_sources for s in ["dust_sweeping", "dry_sweeping", "dusting", "broom"]):
            items.append(
                IndoorActionItem(
                    source="Dry Broom Sweeping",
                    action="Switch from dry broom sweeping to damp cloth mopping and microfibre wiping.",
                    priority="MEDIUM",
                    reason=(
                        "Dry sweeping resuspends coarse settled dust and particulate reservoirs back into breathing air."
                    ),
                )
            )

        # If no specific sources flagged, add baseline source control guidance
        if not items:
            items.append(
                IndoorActionItem(
                    source="Baseline Indoor Air Source Hygiene",
                    action="Avoid indoor burning (incense, coils, candles) and vent cooking spaces safely.",
                    priority="MEDIUM",
                    reason="Preventing indoor combustion emissions is the most cost-effective measure for indoor air quality.",
                )
            )

        return items

    def _evaluate_ventilation(
        self,
        outdoor_category: Optional[str],
        ventilation_available: bool,
    ) -> VentilationAdvisory:
        """Condition-based ventilation guidance tied to outdoor air and combustion safety."""
        backdraft_precaution = (
            "Exhaust-only systems can depressurize rooms and create backdraft risks with combustion appliances "
            "(such as gas geysers or LPG stoves) if adequate replacement air is absent. Follow appliance manufacturer "
            "instructions and obtain professional guidance where combustion appliance safety is uncertain."
        )

        if not ventilation_available:
            return VentilationAdvisory(
                outdoor_aqi_category=outdoor_category,
                strategy="No Direct Operable Ventilation Available",
                guidance=(
                    "This room lacks operable windows or mechanical ventilation vents. "
                    "Focus on indoor source control and mechanical filtration. "
                    "Ensure doorway circulation exists if multiple occupants are present."
                ),
                precautions=[
                    "Ensure adequate air circulation in small, tightly closed rooms with multiple occupants.",
                    backdraft_precaution,
                ],
            )

        if outdoor_category in ["Poor", "Very Poor", "Severe"]:
            return VentilationAdvisory(
                outdoor_aqi_category=outdoor_category,
                strategy="Restrict Outdoor Infiltration & Controlled Ventilation",
                guidance=(
                    f"Outdoor air quality is currently {outdoor_category}. "
                    "Keep external doors and windows closed, especially during morning and late evening hours, to limit outdoor smog entry. "
                    "If natural ventilation is needed, NCDC (2025) advisory mentions the 12 PM to 4 PM afternoon window as conditional guidance "
                    "(note: this is general public-health guidance, not a guarantee of safe outdoor air)."
                ),
                precautions=[
                    "Never block mandatory combustion safety vents or water heater (geyser) flues.",
                    backdraft_precaution,
                    "Do not blindly run high-volume exhaust fans with all windows tightly closed in homes with open-flue gas water heaters.",
                ],
            )
        elif outdoor_category in ["Good", "Satisfactory"]:
            return VentilationAdvisory(
                outdoor_aqi_category=outdoor_category,
                strategy="Controlled Cross-Ventilation",
                guidance=(
                    f"Outdoor air quality is currently {outdoor_category}. "
                    "Opening opposite windows for short periods can help flush out accumulated indoor carbon dioxide, humidity, and cooking odors."
                ),
                precautions=[
                    "Avoid opening windows facing immediately onto heavy idling vehicular traffic.",
                    backdraft_precaution,
                ],
            )
        elif outdoor_category == "Moderate":
            return VentilationAdvisory(
                outdoor_aqi_category=outdoor_category,
                strategy="Selective Brief Ventilation",
                guidance=(
                    "Outdoor air quality is Moderate. Brief ventilation is acceptable if indoor air feels stuffy, "
                    "preferably away from roadside dust sources."
                ),
                precautions=[
                    "Sensitive family members should remain in an interior room while external windows are open.",
                    backdraft_precaution,
                ],
            )
        else:
            return VentilationAdvisory(
                outdoor_aqi_category=None,
                strategy="Precautionary Infiltration Management",
                guidance=(
                    "Outdoor air quality monitoring data is currently unverified. "
                    "Practice sensible infiltration management: keep windows closed during visible outdoor haze, "
                    "and vent cooking areas safely."
                ),
                precautions=[
                    "Never block combustion safety vents or geyser flues.",
                    backdraft_precaution,
                ],
            )

    def _get_affordable_interventions(self, budget: HouseholdBudget, has_purifier: bool) -> List[str]:
        """Affordable household interventions tailored to family budget."""
        interventions = [
            "Damp cloth mopping: Wet-mop floors instead of dry sweeping to capture settled dust without resuspension (zero cost).",
            "Door threshold sealing: Place a rolled damp towel or foam strip along gaps at the bottom of exterior doors to reduce outdoor smog entry (zero or negligible cost).",
            "Range hood venting: Use an externally vented kitchen hood or chimney during cooking; cover frying pans to contain oil droplets.",
        ]

        if not has_purifier:
            if budget == HouseholdBudget.low:
                interventions.append(
                    "Budget prioritization: Zero-cost source control (stopping incense/coils and damp cleaning) eliminates major indoor emissions without purchasing devices."
                )
            else:
                interventions.append(
                    "Purifier selection: If considering an air purifier, verify manufacturer-certified CADR relative to room volume, and avoid unverified ozone-producing devices."
                )
        else:
            interventions.append(
                "Manufacturer maintenance: Follow manufacturer user manual instructions for cleaning the pre-filter and replacing filter cartridges."
            )

        return interventions


# Global service singleton instance
indoor_air_service = IndoorAirService()
