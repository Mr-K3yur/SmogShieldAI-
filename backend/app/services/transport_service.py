"""Deterministic Transportation Service for SmogShield AI.

Implements Feature A (Advisor) and Feature C (Calculator):
- Mode comparison with verified Phase 3 AQI context and Phase 4 NCDC 2025 health guidance
- Strict suppression of walking/cycling recommendations under Poor/Very Poor/Severe AQI
- Strict capacity boundaries (< 125cc, < 1400cc) returning UNAVAILABLE when violated
- Deterministic CO2 formulas (never CO2e), effective distance doubling for round-trips
- Occupancy handling (includes driver; never divides public transport pax-km factors)
- Honest presentation of emissions increases (negative avoided values)
- Zero invention of public transit routes, fares, schedules, or personal exposure scores
"""

import logging
from typing import Dict, List, Optional

from app.schemas.station import AvailabilityType, StationAQIResponse
from app.schemas.transport import (
    AvoidedEmissionsComparison,
    FactorVerificationStatus,
    FuelType,
    TransportComparisonRequest,
    TransportComparisonResponse,
    TransportMode,
    TransportModeResult,
)
from app.services.emission_factor_registry import emission_factor_registry
from app.services.station_service import station_service
from app.services.planner_service import NCDC_2025_ADVISORIES

logger = logging.getLogger(__name__)

CEA_FY26_27_PRIOR_YEAR_WARNING = (
    "Latest published CEA electricity emission factor is from FY 2025-26 (Version 22.0, published August 2026); "
    "used as a prior-year estimate because the official FY 2026-27 factor is not yet available."
)

WALK_CYCLE_LIFECYCLE_DISCLOSURE = (
    "This calculation reflects direct operational tailpipe emissions only (0.0 kg CO2). "
    "Lifecycle emissions — including bicycle manufacturing, food caloric intake overhead, and transport infrastructure — "
    "are excluded from this scope."
)


class TransportService:
    """Service implementing transport emissions calculations and NCDC-aligned commute advisory."""

    def calculate_mode_emissions(
        self,
        mode: TransportMode,
        distance_km: float,
        round_trip: bool = False,
        occupancy: int = 1,
        fuel_type: Optional[FuelType] = None,
        engine_capacity_cc: Optional[int] = None,
        user_ev_kwh_per_km: Optional[float] = None,
        user_metro_kwh_per_pax_km: Optional[float] = None,
        aqi_category: str = "Unknown",
    ) -> TransportModeResult:
        """Deterministically calculate passenger emissions for an individual transport mode."""
        effective_distance = distance_km * 2.0 if round_trip else distance_km
        calc_trace: List[str] = [
            f"Trip configuration: distance={distance_km} km, round_trip={round_trip} -> effective_distance={effective_distance} km",
            f"Vehicle occupancy: {occupancy} total person(s) (including driver)"
        ]

        # 1. Active Travel: Walking & Cycling
        if mode in [TransportMode.walking, TransportMode.cycling]:
            is_contraindicated = aqi_category in ["Poor", "Very Poor", "Severe"]
            health_note = None
            if is_contraindicated:
                health_note = (
                    f"NCDC (2025) advisory advises avoiding outdoor physical exertion/activities under {aqi_category} air quality. "
                    f"Walking/cycling is not recommended as an active commute choice during elevated smog."
                )
            else:
                health_note = f"Active travel can proceed with standard physical awareness under {aqi_category} air."

            calc_trace.append(f"{mode.value.title()}: 0.0 kg CO2 direct operational tailpipe emissions.")

            return TransportModeResult(
                mode=mode,
                is_available=True,
                factor_id_used="ZERO_DIRECT_TAILPIPE",
                factor_value=0.0,
                factor_unit="kg CO2/km",
                factor_status=FactorVerificationStatus.VERIFIED_CURRENT,
                effective_distance_km=effective_distance,
                occupancy=occupancy,
                total_vehicle_emissions_kg_co2=0.0,
                passenger_emissions_kg_co2=0.0,
                is_user_guided=False,
                health_guidance_note=health_note,
                is_recommended_for_commute=not is_contraindicated,
                lifecycle_disclosure=WALK_CYCLE_LIFECYCLE_DISCLOSURE,
                calculation_trace=calc_trace,
            )

        # 2. Public Transit: Intracity Bus (SRTU pax-km factor)
        if mode == TransportMode.intracity_bus:
            entry = emission_factor_registry.get_factor("INTRACITY_BUS_SRTU")
            pax_co2 = round(effective_distance * entry.default_value, 4)
            calc_trace.extend([
                f"Factor: {entry.factor_id} = {entry.default_value} {entry.unit} (SRTU weighted average)",
                "Factor is ALREADY in passenger-kilometers (pax-km). Occupancy divisor is strictly NOT applied.",
                f"Passenger CO2 = {effective_distance} km * {entry.default_value} = {pax_co2} kg CO2"
            ])
            return TransportModeResult(
                mode=mode,
                is_available=True,
                factor_id_used=entry.factor_id,
                factor_value=entry.default_value,
                factor_unit=entry.unit,
                factor_status=entry.verification_status,
                effective_distance_km=effective_distance,
                occupancy=occupancy,
                total_vehicle_emissions_kg_co2=None,  # Not applicable to shared SRTU fleet
                passenger_emissions_kg_co2=pax_co2,
                is_user_guided=False,
                calculation_trace=calc_trace,
            )

        # 3. Metro Rail: User-Guided Only (National factor is UNAVAILABLE)
        if mode == TransportMode.metro:
            if user_metro_kwh_per_pax_km is None or user_metro_kwh_per_pax_km <= 0:
                calc_trace.append(
                    "Metro calculation is UNAVAILABLE: Indian Railways factor explicitly excludes MRTS systems, "
                    "and no single national passenger-km factor is published in an audited standard."
                )
                return TransportModeResult(
                    mode=mode,
                    is_available=False,
                    unavailable_reason=(
                        "National Metro emission factor is UNAVAILABLE. S2 rail factor excludes MRTS. "
                        "To calculate metro emissions, provide your city operator's specific energy consumption (kWh/pax-km)."
                    ),
                    effective_distance_km=effective_distance,
                    occupancy=occupancy,
                    calculation_trace=calc_trace,
                )

            grid_factor = emission_factor_registry.get_grid_factor()
            pax_co2 = round(effective_distance * user_metro_kwh_per_pax_km * grid_factor.default_value, 4)
            calc_trace.extend([
                f"User-provided metro specific energy consumption = {user_metro_kwh_per_pax_km} kWh/pax-km",
                f"CEA grid factor: {grid_factor.default_value} {grid_factor.unit} ({grid_factor.applicable_fiscal_year})",
                "Factor is already per passenger-km. Occupancy divisor is strictly NOT applied.",
                f"Passenger CO2 = {effective_distance} km * {user_metro_kwh_per_pax_km} kWh/pax-km * {grid_factor.default_value} kg/kWh = {pax_co2} kg CO2",
                CEA_FY26_27_PRIOR_YEAR_WARNING
            ])
            return TransportModeResult(
                mode=mode,
                is_available=True,
                factor_id_used=grid_factor.factor_id,
                factor_value=grid_factor.default_value,
                factor_unit=grid_factor.unit,
                factor_status=grid_factor.verification_status,
                effective_distance_km=effective_distance,
                occupancy=occupancy,
                passenger_emissions_kg_co2=pax_co2,
                is_user_guided=True,
                user_guided_source_note="Calculated using user-entered metro SEC and official CEA FY 2025-26 grid emission factor.",
                calculation_trace=calc_trace,
            )

        # 4. Electric Vehicles (EV): User-Guided Only (National vehicle factor is UNAVAILABLE)
        if mode == TransportMode.electric_vehicle:
            if user_ev_kwh_per_km is None or user_ev_kwh_per_km <= 0:
                calc_trace.append(
                    "EV calculation is UNAVAILABLE: No certified national vehicle-km factor is published in an audited Indian registry."
                )
                return TransportModeResult(
                    mode=mode,
                    is_available=False,
                    unavailable_reason=(
                        "Electric vehicle emission factor is UNAVAILABLE without rated vehicle consumption. "
                        "Provide your vehicle's energy consumption (kWh/km) to calculate indirect emissions via CEA grid factor."
                    ),
                    effective_distance_km=effective_distance,
                    occupancy=occupancy,
                    calculation_trace=calc_trace,
                )

            grid_factor = emission_factor_registry.get_grid_factor()
            veh_co2 = round(effective_distance * user_ev_kwh_per_km * grid_factor.default_value, 4)
            pax_co2 = round(veh_co2 / occupancy, 4)
            calc_trace.extend([
                f"User-provided EV energy consumption = {user_ev_kwh_per_km} kWh/km",
                f"CEA grid factor: {grid_factor.default_value} {grid_factor.unit} ({grid_factor.applicable_fiscal_year})",
                f"Total vehicle emissions = {effective_distance} km * {user_ev_kwh_per_km} kWh/km * {grid_factor.default_value} kg/kWh = {veh_co2} kg CO2",
                f"Per-passenger share = {veh_co2} kg CO2 / {occupancy} occupant(s) = {pax_co2} kg CO2",
                CEA_FY26_27_PRIOR_YEAR_WARNING
            ])
            return TransportModeResult(
                mode=mode,
                is_available=True,
                factor_id_used=grid_factor.factor_id,
                factor_value=grid_factor.default_value,
                factor_unit=grid_factor.unit,
                factor_status=grid_factor.verification_status,
                effective_distance_km=effective_distance,
                occupancy=occupancy,
                total_vehicle_emissions_kg_co2=veh_co2,
                passenger_emissions_kg_co2=pax_co2,
                is_user_guided=True,
                user_guided_source_note="Calculated using user-entered vehicle kWh/km and official CEA FY 2025-26 grid factor.",
                calculation_trace=calc_trace,
            )

        # 5. Carpool: Uses car factor with occupancy > 1
        if mode == TransportMode.carpool:
            actual_occupancy = max(2, occupancy)
            resolved_fuel = fuel_type or FuelType.petrol
            lookup_mode = "diesel_car" if resolved_fuel == FuelType.diesel else "petrol_car"
            factor_entry = emission_factor_registry.resolve_road_factor(
                mode=lookup_mode,
                engine_capacity_cc=engine_capacity_cc,
            )
            if factor_entry is None:
                calc_trace.append(f"Carpool calculation UNAVAILABLE: Car with engine capacity {engine_capacity_cc} cc violates strict < 1400 cc boundary.")
                return TransportModeResult(
                    mode=mode,
                    is_available=False,
                    unavailable_reason="Carpool factor UNAVAILABLE. Passenger car capacity must be strictly < 1400 cc per India GHG 2015 paper.",
                    effective_distance_km=effective_distance,
                    occupancy=actual_occupancy,
                    calculation_trace=calc_trace,
                )

            veh_co2 = round(effective_distance * factor_entry.default_value, 4)
            pax_co2 = round(veh_co2 / actual_occupancy, 4)
            calc_trace.extend([
                f"Carpool base vehicle: {factor_entry.factor_id} = {factor_entry.default_value} {factor_entry.unit} (uplifted)",
                f"Vehicle CO2 = {effective_distance} km * {factor_entry.default_value} = {veh_co2} kg CO2",
                f"Carpool passenger allocation = {veh_co2} / {actual_occupancy} occupants = {pax_co2} kg CO2"
            ])
            return TransportModeResult(
                mode=mode,
                is_available=True,
                factor_id_used=factor_entry.factor_id,
                factor_value=factor_entry.default_value,
                factor_unit=factor_entry.unit,
                factor_status=factor_entry.verification_status,
                effective_distance_km=effective_distance,
                occupancy=actual_occupancy,
                total_vehicle_emissions_kg_co2=veh_co2,
                passenger_emissions_kg_co2=pax_co2,
                calculation_trace=calc_trace,
            )

        # 6. Standard Road Vehicles: Motorcycle, Petrol Car, Diesel Car, CNG Auto
        factor_entry = emission_factor_registry.resolve_road_factor(
            mode=mode.value,
            engine_capacity_cc=engine_capacity_cc,
        )
        if factor_entry is None:
            boundary_desc = "< 125 cc" if mode == TransportMode.petrol_motorcycle else "< 1400 cc"
            calc_trace.append(f"Mode {mode.value} UNAVAILABLE: Engine capacity {engine_capacity_cc} cc violates strict {boundary_desc} boundary.")
            return TransportModeResult(
                mode=mode,
                is_available=False,
                unavailable_reason=f"Emission factor UNAVAILABLE. Engine capacity must be strictly {boundary_desc} per India GHG Program (2015).",
                effective_distance_km=effective_distance,
                occupancy=occupancy,
                calculation_trace=calc_trace,
            )

        veh_co2 = round(effective_distance * factor_entry.default_value, 4)
        pax_co2 = round(veh_co2 / occupancy, 4)
        calc_trace.extend([
            f"Factor: {factor_entry.factor_id} = {factor_entry.default_value} {factor_entry.unit} ({factor_entry.verification_status.value})",
            f"Vehicle CO2 = {effective_distance} km * {factor_entry.default_value} = {veh_co2} kg CO2",
            f"Passenger CO2 = {veh_co2} / {occupancy} occupant(s) = {pax_co2} kg CO2"
        ])

        return TransportModeResult(
            mode=mode,
            is_available=True,
            factor_id_used=factor_entry.factor_id,
            factor_value=factor_entry.default_value,
            factor_unit=factor_entry.unit,
            factor_status=factor_entry.verification_status,
            effective_distance_km=effective_distance,
            occupancy=occupancy,
            total_vehicle_emissions_kg_co2=veh_co2,
            passenger_emissions_kg_co2=pax_co2,
            calculation_trace=calc_trace,
        )

    async def compare_transport_modes(self, request: TransportComparisonRequest) -> TransportComparisonResponse:
        """Compare baseline travel against selected alternatives with Phase 3 AQI and Phase 4 guidance."""
        raw_station_data = station_service.get_station_aqi(request.station_id)
        if hasattr(raw_station_data, "__await__"):
            station_data: StationAQIResponse = await raw_station_data
        else:
            station_data: StationAQIResponse = raw_station_data

        aqi_available = station_data.availability == AvailabilityType.AVAILABLE
        category = station_data.category if aqi_available else "Unknown"
        current_aqi = station_data.overall_aqi if aqi_available else None

        base_advisory = NCDC_2025_ADVISORIES.get(category, NCDC_2025_ADVISORIES["Unknown"])
        general_adv = base_advisory["general_population"]
        vulnerable_adv = base_advisory["vulnerable_population"]

        effective_dist = request.distance_km * 2.0 if request.round_trip else request.distance_km

        # Evaluate baseline mode
        baseline_result = self.calculate_mode_emissions(
            mode=request.current_mode,
            distance_km=request.distance_km,
            round_trip=request.round_trip,
            occupancy=request.occupancy,
            fuel_type=request.fuel_type,
            engine_capacity_cc=request.engine_capacity_cc,
            user_ev_kwh_per_km=request.user_ev_kwh_per_km,
            user_metro_kwh_per_pax_km=request.user_metro_kwh_per_pax_km,
            aqi_category=category,
        )

        alt_results: List[TransportModeResult] = []
        avoided_comparisons: List[AvoidedEmissionsComparison] = []

        for alt_mode in request.alternatives:
            # Default alternative occupancy to 1 (or 2 for carpool)
            alt_occ = 2 if alt_mode == TransportMode.carpool else 1
            alt_res = self.calculate_mode_emissions(
                mode=alt_mode,
                distance_km=request.distance_km,
                round_trip=request.round_trip,
                occupancy=alt_occ,
                user_ev_kwh_per_km=request.user_ev_kwh_per_km,
                user_metro_kwh_per_pax_km=request.user_metro_kwh_per_pax_km,
                aqi_category=category,
            )
            alt_results.append(alt_res)

            # Compute avoided emissions comparison
            if baseline_result.is_available and baseline_result.passenger_emissions_kg_co2 is not None:
                base_pax = baseline_result.passenger_emissions_kg_co2
                if alt_res.is_available and alt_res.passenger_emissions_kg_co2 is not None:
                    alt_pax = alt_res.passenger_emissions_kg_co2
                    avoided = round(base_pax - alt_pax, 4)
                    is_increase = avoided < 0.0
                    weekly = round(avoided * request.trips_per_week, 4)
                    monthly = round(weekly * 4.33, 4)

                    if is_increase:
                        summary = f"Switching to {alt_mode.value.replace('_', ' ')} results in an estimated emissions INCREASE of {abs(avoided)} kg CO2 per trip."
                    elif avoided == 0.0:
                        summary = f"Emissions are identical to baseline ({base_pax} kg CO2 per trip)."
                    else:
                        summary = f"Switching to {alt_mode.value.replace('_', ' ')} avoids an estimated {avoided} kg CO2 per trip."

                    avoided_comparisons.append(
                        AvoidedEmissionsComparison(
                            alternative_mode=alt_mode,
                            baseline_passenger_emissions_kg_co2=base_pax,
                            alternative_passenger_emissions_kg_co2=alt_pax,
                            avoided_kg_co2_per_trip=avoided,
                            is_emissions_increase=is_increase,
                            projected_weekly_saving_kg_co2=weekly,
                            projected_monthly_saving_kg_co2=monthly,
                            comparison_summary=summary,
                        )
                    )
                else:
                    avoided_comparisons.append(
                        AvoidedEmissionsComparison(
                            alternative_mode=alt_mode,
                            baseline_passenger_emissions_kg_co2=base_pax,
                            alternative_passenger_emissions_kg_co2=None,
                            avoided_kg_co2_per_trip=None,
                            is_emissions_increase=False,
                            comparison_summary=f"Avoided emissions comparison UNAVAILABLE: {alt_res.unavailable_reason or 'No verified factor.'}",
                        )
                    )

        disclaimers: List[str] = [
            "SmogShield AI does not invent public transport routes, fares, travel times, or schedules.",
            "Public transit emissions represent operational fleet averages and do not guarantee lower personal pollution exposure.",
            "Historical road factors are sourced from India GHG Program (2015) stakeholder consultation paper and carry HISTORICAL_PROVISIONAL status.",
            "All-India electricity grid factor reflects CEA Version 22.0 (FY 2025-26) and serves as a prior-year estimate for FY 2026-27.",
        ]

        limitations: List[str] = [
            "Calculations reflect direct operational tailpipe CO2 emissions only (excluding lifecycle vehicle manufacture and energy upstream).",
            "Projected weekly and monthly savings are mathematical estimates based on trip frequency and must not be confused with actual completed trips.",
        ]

        return TransportComparisonResponse(
            station_id=station_data.station.station_id,
            station_name=station_data.station.station_name,
            city=station_data.station.city,
            current_aqi=current_aqi,
            aqi_category=category,
            ncdc_general_advisory=general_adv,
            ncdc_vulnerable_advisory=vulnerable_adv,
            effective_distance_km=effective_dist,
            round_trip=request.round_trip,
            baseline_result=baseline_result,
            alternative_results=alt_results,
            avoided_comparisons=avoided_comparisons,
            disclaimers=disclaimers,
            limitations=limitations,
        )


transport_service = TransportService()
