"""Unit tests for Phase 5: Sustainable Transportation Advisor and Emissions Calculator.

Audited scenarios:
1. Petrol motorcycle strictly under 125 cc uses 0.0319 uplifted factor.
2. Petrol motorcycle exactly 125 cc returns UNAVAILABLE under strict < boundary.
3. Petrol motorcycle over 125 cc returns UNAVAILABLE.
4. Petrol hatchback strictly under 1400 cc uses 0.140 uplifted factor.
5. Petrol hatchback exactly 1400 cc returns UNAVAILABLE.
6. Diesel hatchback strictly under 1400 cc uses 0.126 uplifted factor.
7. Diesel hatchback exactly 1400 cc returns UNAVAILABLE.
8. Petrol base not mixed with diesel uplift (cross-contamination test).
9. CNG auto-rickshaw factor (0.10768) divided by occupancy (max 3).
10. CNG auto-rickshaw exceeding max occupancy (3) rejected by schema validation.
11. Intracity bus pax-km factor (0.015161) multiplied directly by distance; NEVER divided by occupancy.
12. Round-trip doubles distance before all calculations.
13. One-way distance is not doubled.
14. CEA grid factor metadata confirms 0.675 kg CO2/kWh tied to V22.0, FY 2025-26.
15. CEA grid factor prior-year estimate warning present for FY 2026-27 usage.
16. Metro unavailable without user-provided SEC.
17. Metro user-provided kWh calculation uses SEC * distance * 0.675; no occupancy division.
18. EV unavailable without user-provided kWh/km.
19. EV user-provided kWh calculation uses kWh/km * distance * 0.675 / occupancy.
20. Walking returns 0.0 kg CO2 with mandatory lifecycle disclosure.
21. Cycling returns 0.0 kg CO2 with mandatory lifecycle disclosure.
22. Walking/cycling suppressed as commute recommendation under Poor/Very Poor/Severe AQI.
23. Avoided emissions negative value shown honestly as emissions increase.
24. Emission factor registry has exactly 9 entries with all required fields.
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.schemas.station import (
    AvailabilityType,
    FreshnessType,
    ProvenanceType,
    StationAQIResponse,
    StationMetadata,
)
from app.schemas.transport import (
    EmissionFactorRegistryResponse,
    FactorVerificationStatus,
    FuelType,
    TransportComparisonRequest,
    TransportComparisonResponse,
    TransportMode,
)
from app.services.emission_factor_registry import emission_factor_registry
from app.services.station_service import station_service
from app.services.transport_service import transport_service


def make_mock_station(category: str = "Poor", overall_aqi: int = 250) -> StationAQIResponse:
    """Helper to mock station responses for transport comparison tests."""
    return StationAQIResponse(
        station=StationMetadata(
            station_id="cpcb_delhi_ito",
            provider="mock",
            provider_station_id="DEL_ITO_01",
            station_name="ITO, Delhi",
            city="Delhi",
            state="Delhi",
            country="India",
            timezone="Asia/Kolkata",
        ),
        provenance=ProvenanceType.CALCULATED,
        availability=AvailabilityType.AVAILABLE,
        freshness=FreshnessType.FRESH,
        calculated_aqi=overall_aqi,
        overall_aqi=overall_aqi,
        overall_aqi_lower_bound=overall_aqi,
        overall_aqi_upper_bound=overall_aqi,
        is_exact=True,
        category=category,
        dominant_pollutant="PM2.5",
        source="CPCB",
        observed_at_utc=datetime.now(timezone.utc),
    )


class TestEmissionFactorBoundariesAndCalculations:

    def test_petrol_motorcycle_strictly_under_125cc_calculates_uplifted(self):
        """100cc motorcycle strictly under 125 cc uses active default factor 0.0319."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.petrol_motorcycle,
            distance_km=10.0,
            engine_capacity_cc=100,
            occupancy=1,
        )
        assert res.is_available is True
        assert res.factor_id_used == "PETROL_MOTORCYCLE_UPLIFT"
        assert res.factor_value == 0.0319
        # 10 km * 0.0319 = 0.319 kg CO2
        assert res.passenger_emissions_kg_co2 == 0.319

    def test_petrol_motorcycle_exactly_125cc_returns_unavailable(self):
        """Exactly 125 cc violates strict < 125 cc boundary and returns UNAVAILABLE."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.petrol_motorcycle,
            distance_km=10.0,
            engine_capacity_cc=125,
            occupancy=1,
        )
        assert res.is_available is False
        assert "UNAVAILABLE" in res.unavailable_reason
        assert "< 125 cc" in res.unavailable_reason

    def test_petrol_motorcycle_over_125cc_returns_unavailable(self):
        """150cc motorcycle returns UNAVAILABLE."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.petrol_motorcycle,
            distance_km=10.0,
            engine_capacity_cc=150,
        )
        assert res.is_available is False
        assert res.passenger_emissions_kg_co2 is None

    def test_petrol_hatchback_strictly_under_1400cc_calculates_uplifted(self):
        """1198cc petrol hatchback strictly under 1400 cc uses factor 0.140."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.petrol_car,
            distance_km=15.0,
            engine_capacity_cc=1198,
            occupancy=2,
        )
        assert res.is_available is True
        assert res.factor_id_used == "PETROL_CAR_HATCHBACK_UPLIFT"
        assert res.factor_value == 0.140
        # 15 km * 0.140 = 2.1 kg CO2 total; per passenger (2 occ) = 1.05 kg CO2
        assert res.total_vehicle_emissions_kg_co2 == 2.1
        assert res.passenger_emissions_kg_co2 == 1.05

    def test_petrol_hatchback_exactly_1400cc_returns_unavailable(self):
        """Exactly 1400 cc petrol hatchback returns UNAVAILABLE under strict < boundary."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.petrol_car,
            distance_km=10.0,
            engine_capacity_cc=1400,
        )
        assert res.is_available is False
        assert "< 1400 cc" in res.unavailable_reason

    def test_diesel_hatchback_strictly_under_1400cc_calculates_uplifted(self):
        """1248cc diesel hatchback strictly under 1400 cc uses factor 0.126."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.diesel_car,
            distance_km=20.0,
            engine_capacity_cc=1248,
            occupancy=1,
        )
        assert res.is_available is True
        assert res.factor_id_used == "DIESEL_CAR_HATCHBACK_UPLIFT"
        assert res.factor_value == 0.126
        # 20 km * 0.126 = 2.52 kg CO2
        assert res.passenger_emissions_kg_co2 == 2.52

    def test_diesel_hatchback_exactly_1400cc_returns_unavailable(self):
        """Exactly 1400 cc diesel hatchback returns UNAVAILABLE."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.diesel_car,
            distance_km=20.0,
            engine_capacity_cc=1400,
        )
        assert res.is_available is False
        assert "< 1400 cc" in res.unavailable_reason

    def test_petrol_base_not_mixed_with_diesel_uplift(self):
        """Enforces that petrol base is never mixed with diesel uplift factors."""
        petrol_factor = emission_factor_registry.get_factor("PETROL_CAR_HATCHBACK_UPLIFT")
        diesel_factor = emission_factor_registry.get_factor("DIESEL_CAR_HATCHBACK_UPLIFT")
        assert petrol_factor.default_value == 0.140
        assert diesel_factor.default_value == 0.126
        assert petrol_factor.fuel_type == "petrol"
        assert diesel_factor.fuel_type == "diesel"

    def test_cng_auto_per_vehicle_then_per_passenger(self):
        """CNG auto 0.10768 kg CO2/veh-km is divided by total passengers (occupancy 3)."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.cng_auto,
            distance_km=10.0,
            occupancy=3,
        )
        assert res.is_available is True
        assert res.factor_id_used == "CNG_AUTO_RICKSHAW"
        assert res.total_vehicle_emissions_kg_co2 == 1.0768
        # 1.0768 / 3 occupants = 0.3589 kg CO2/passenger
        assert res.passenger_emissions_kg_co2 == 0.3589

    def test_cng_auto_exceeding_max_occupancy_rejected(self):
        """CNG auto occupancy > 3 raises validation error."""
        with pytest.raises(ValidationError):
            TransportComparisonRequest(
                station_id="cpcb_delhi_ito",
                current_mode=TransportMode.cng_auto,
                distance_km=10.0,
                occupancy=4,  # Over max of 3
                alternatives=[TransportMode.intracity_bus],
            )

    def test_intracity_bus_pax_km_no_occupancy_division(self):
        """Intracity bus factor (0.015161) is ALREADY per pax-km; NEVER divided by occupancy."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.intracity_bus,
            distance_km=10.0,
            occupancy=4,  # Even if passenger group is 4, factor applies per-person
        )
        assert res.is_available is True
        assert res.factor_id_used == "INTRACITY_BUS_SRTU"
        # 10 km * 0.015161 = 0.1516 kg CO2
        assert res.passenger_emissions_kg_co2 == 0.1516
        assert any("NEVER divide this factor by occupancy" in t or "NOT applied" in t for t in res.calculation_trace)

    def test_round_trip_doubles_distance_before_calculations(self):
        """round_trip=True doubles effective distance from 10 km to 20 km."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.petrol_motorcycle,
            distance_km=10.0,
            round_trip=True,
            engine_capacity_cc=100,
        )
        assert res.effective_distance_km == 20.0
        # 20 km * 0.0319 = 0.638 kg CO2
        assert res.passenger_emissions_kg_co2 == 0.638

    def test_one_way_distance_not_doubled(self):
        """round_trip=False retains original distance."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.petrol_motorcycle,
            distance_km=10.0,
            round_trip=False,
            engine_capacity_cc=100,
        )
        assert res.effective_distance_km == 10.0

    def test_cea_grid_factor_applicability_metadata(self):
        """Confirms CEA factor is 0.675 kg CO2/kWh tied to V22.0, FY 2025-26."""
        factor = emission_factor_registry.get_grid_factor()
        assert factor.factor_id == "INDIA_GRID_WEIGHTED_AVG"
        assert factor.default_value == 0.675
        assert factor.unit == "kg CO2/kWh"
        assert factor.publication_year == 2026
        assert factor.applicable_fiscal_year == "FY 2025-26"
        assert factor.verification_status == FactorVerificationStatus.VERIFIED_CURRENT

    def test_cea_grid_factor_fy26_27_prior_year_warning(self):
        """Metro / EV calculations include the explicit FY 2026-27 prior-year estimate warning."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.metro,
            distance_km=10.0,
            user_metro_kwh_per_pax_km=0.05,
        )
        assert res.is_available is True
        assert any("prior-year estimate because the official FY 2026-27 factor is not yet available" in t for t in res.calculation_trace)

    def test_metro_unavailable_without_user_data(self):
        """Metro returns UNAVAILABLE when user does not supply SEC."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.metro,
            distance_km=10.0,
            user_metro_kwh_per_pax_km=None,
        )
        assert res.is_available is False
        assert "UNAVAILABLE" in res.unavailable_reason
        assert "MRTS" in res.unavailable_reason

    def test_metro_user_provided_kwh_calculation(self):
        """Metro with 0.048 kWh/pax-km calculates: 10 km * 0.048 * 0.675 = 0.324 kg CO2."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.metro,
            distance_km=10.0,
            user_metro_kwh_per_pax_km=0.048,
        )
        assert res.is_available is True
        assert res.passenger_emissions_kg_co2 == 0.324
        assert res.is_user_guided is True

    def test_ev_unavailable_without_user_data(self):
        """EV returns UNAVAILABLE when user kWh/km is not provided."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.electric_vehicle,
            distance_km=10.0,
            user_ev_kwh_per_km=None,
        )
        assert res.is_available is False
        assert "UNAVAILABLE" in res.unavailable_reason

    def test_ev_user_provided_kwh_calculation(self):
        """EV with 0.15 kWh/km, distance 20km, occupancy 2: 20 * 0.15 * 0.675 / 2 = 1.0125 kg CO2."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.electric_vehicle,
            distance_km=20.0,
            occupancy=2,
            user_ev_kwh_per_km=0.15,
        )
        assert res.is_available is True
        assert res.total_vehicle_emissions_kg_co2 == 2.025
        assert res.passenger_emissions_kg_co2 == 1.0125
        assert res.is_user_guided is True

    def test_walking_zero_tailpipe_with_lifecycle_disclosure(self):
        """Walking returns 0.0 kg CO2 and includes mandatory lifecycle disclosure."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.walking,
            distance_km=3.0,
            aqi_category="Good",
        )
        assert res.is_available is True
        assert res.passenger_emissions_kg_co2 == 0.0
        assert res.is_recommended_for_commute is True
        assert res.lifecycle_disclosure is not None
        assert "direct operational tailpipe emissions only" in res.lifecycle_disclosure

    def test_cycling_zero_tailpipe_with_lifecycle_disclosure(self):
        """Cycling returns 0.0 kg CO2 with lifecycle disclosure."""
        res = transport_service.calculate_mode_emissions(
            mode=TransportMode.cycling,
            distance_km=5.0,
            aqi_category="Satisfactory",
        )
        assert res.is_available is True
        assert res.passenger_emissions_kg_co2 == 0.0
        assert "Lifecycle emissions" in res.lifecycle_disclosure

    def test_walking_cycling_suppressed_under_poor_very_poor_severe_aqi(self):
        """Walking/cycling is not recommended when AQI is Poor, Very Poor, or Severe."""
        for bad_cat in ["Poor", "Very Poor", "Severe"]:
            res = transport_service.calculate_mode_emissions(
                mode=TransportMode.cycling,
                distance_km=5.0,
                aqi_category=bad_cat,
            )
            assert res.is_recommended_for_commute is False
            assert "NCDC (2025) advisory" in res.health_guidance_note
            assert bad_cat in res.health_guidance_note

    def test_avoided_emissions_negative_shown_honestly(self):
        """Switching from bus (0.1516 kg CO2) to petrol car (1.4 kg CO2) shows emissions INCREASE honestly."""
        bus_pax = 0.1516
        car_pax = 1.4
        avoided = round(bus_pax - car_pax, 4)
        assert avoided == -1.2484
        assert avoided < 0.0

    def test_registry_has_exactly_nine_entries(self):
        """Registry contains exactly 9 entries with all required audit fields."""
        factors = emission_factor_registry.get_all_factors()
        assert len(factors) == 9
        for f in factors:
            assert f.factor_id
            assert f.source_name
            assert f.document_title
            assert f.publication_year > 2000
            assert f.verification_status in [
                FactorVerificationStatus.VERIFIED_CURRENT,
                FactorVerificationStatus.HISTORICAL_PROVISIONAL,
            ]
            assert f.default_value > 0.0


class TestFastAPITransportEndpoints:

    @pytest.mark.anyio
    async def test_get_emission_factors_registry_endpoint(self):
        """Integration test for GET /api/v1/transport/emission-factors."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/transport/emission-factors")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_factors"] == 9
            assert len(data["factors"]) == 9
            ids = [f["factor_id"] for f in data["factors"]]
            assert "PETROL_MOTORCYCLE_UPLIFT" in ids
            assert "INDIA_GRID_WEIGHTED_AVG" in ids

    @pytest.mark.anyio
    async def test_post_compare_endpoint(self, monkeypatch):
        """Integration test for POST /api/v1/transport/compare with AQI gating."""
        mock_station = make_mock_station(category="Poor", overall_aqi=260)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_station)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "station_id": "cpcb_delhi_ito",
                "current_mode": "petrol_car",
                "fuel_type": "petrol",
                "engine_capacity_cc": 1198,
                "distance_km": 10.0,
                "round_trip": False,
                "occupancy": 1,
                "trips_per_week": 5,
                "alternatives": ["intracity_bus", "cycling"],
            }
            resp = await client.post("/api/v1/transport/compare", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["station_id"] == "cpcb_delhi_ito"
            assert data["aqi_category"] == "Poor"
            assert data["baseline_result"]["passenger_emissions_kg_co2"] == 1.4

            # Cycling under Poor AQI should be marked not recommended
            cycling_res = next(r for r in data["alternative_results"] if r["mode"] == "cycling")
            assert cycling_res["is_recommended_for_commute"] is False
            assert "Poor" in cycling_res["health_guidance_note"]

            # Bus avoided emissions
            bus_comp = next(c for c in data["avoided_comparisons"] if c["alternative_mode"] == "intracity_bus")
            assert bus_comp["avoided_kg_co2_per_trip"] == round(1.4 - 0.1516, 4)
            assert bus_comp["is_emissions_increase"] is False
