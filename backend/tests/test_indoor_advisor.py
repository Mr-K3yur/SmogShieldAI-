"""Comprehensive tests for Phase 4: Indoor Air Quality Advisor and Purifier Sizing Engine.

Audited and verified against engineering physics and safety standards:
1. Room Volume calculation = L × W × H.
2. CADR unit conversion: 1 CFM = 1.699 m³/h.
3. Theoretical estimated ACH = CADR / Room Volume.
4. No automatically assigned target ACH (target ACH is strictly optional).
5. No universal ACH adequacy labels (e.g. >=4 adequate, <2.5 undersized removed).
6. Target comparison is performed ONLY when the user explicitly provides target_ach.
7. Without user target, returns numerical estimated ACH without labelling it as safe or adequate.
8. Explains clean air delivery depends on fan speed, filter condition, leakage, placement, and mixing.
9. Filter type is flagged as user-reported and not independently laboratory verified.
10. Sizing fine particles using smoke_cadr when manufacturer declared.
11. Manufacturer-specific filter maintenance (no generic intervals).
12. Kitchen ventilation safety: externally vented range hoods and combustion backdraft warning.
13. Houseplant PM2.5 air-cleaning claims debunked.
14. No indoor AQI fabrication without real calibrated sensors.
15. REST API endpoint: POST /api/v1/advisor/indoor-assessment.
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.indoor import (
    CADRUnit,
    HouseholdBudget,
    IndoorAssessmentRequest,
    IndoorAssessmentResponse,
)
from app.schemas.station import (
    AvailabilityType,
    FreshnessType,
    ProvenanceType,
    StationAQIResponse,
    StationMetadata,
)
from app.services.indoor_air_service import indoor_air_service
from app.services.station_service import station_service


def make_mock_outdoor_station(category: str = "Poor") -> StationAQIResponse:
    """Helper to generate mock outdoor station responses."""
    return StationAQIResponse(
        station=StationMetadata(
            station_id="test_outdoor_station",
            provider="mock",
            provider_station_id="TEST_OUT_01",
            station_name="Outdoor Station",
            city="Delhi",
            state="Delhi",
        ),
        provenance=ProvenanceType.CALCULATED,
        availability=AvailabilityType.AVAILABLE,
        freshness=FreshnessType.FRESH,
        overall_aqi=250 if category == "Poor" else 40,
        is_exact=True,
        category=category,
        dominant_pollutant="PM2.5",
        source="Test Provider",
        observed_at_utc=datetime.now(timezone.utc),
    )


# =====================================================================
# 1. GEOMETRY, CADR CONVERSIONS & ACH CALCULATIONS
# =====================================================================

class TestIndoorCalculations:
    @pytest.mark.anyio
    async def test_room_volume_calculation(self):
        """Room Volume = Length × Width × Ceiling Height."""
        req = IndoorAssessmentRequest(
            room_length_m=5.0,
            room_width_m=4.0,
            ceiling_height_m=3.0,
        )
        resp: IndoorAssessmentResponse = await indoor_air_service.assess_room(req)
        assert resp.room_volume_m3 == 60.0
        assert resp.room_dimensions.length_m == 5.0
        assert resp.room_dimensions.width_m == 4.0
        assert resp.room_dimensions.height_m == 3.0

    @pytest.mark.anyio
    async def test_cadr_conversion_cfm_to_m3h(self):
        """Converts CADR in CFM to m³/h using 1 CFM = 1.699 m³/h."""
        # 200 CFM * 1.699 = 339.8 m³/h
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=3.5,
            ceiling_height_m=3.0,
            has_air_purifier=True,
            cadr=200.0,
            cadr_unit=CADRUnit.cfm,
        )
        resp = await indoor_air_service.assess_room(req)
        assert resp.available_cadr_cfm == 200.0
        assert resp.available_cadr_m3h == 339.8

    @pytest.mark.anyio
    async def test_cadr_conversion_m3h_to_cfm(self):
        """Converts CADR in m³/h to CFM using 1 CFM = 1.699 m³/h."""
        # 339.8 m³/h / 1.699 = 200.0 CFM
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=3.5,
            ceiling_height_m=3.0,
            has_air_purifier=True,
            cadr=339.8,
            cadr_unit=CADRUnit.m3_per_hour,
        )
        resp = await indoor_air_service.assess_room(req)
        assert resp.available_cadr_m3h == 339.8
        assert resp.available_cadr_cfm == 200.0

    @pytest.mark.anyio
    async def test_ach_calculation_without_target(self):
        """Calculates ACH = CADR / Volume. Without target, returns numerical ACH without adequacy label."""
        # Volume = 4.0 * 3.5 * 3.0 = 42.0 m³
        # CADR = 339.8 m³/h -> ACH = 339.8 / 42.0 = 8.09
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=3.5,
            ceiling_height_m=3.0,
            has_air_purifier=True,
            cadr=339.8,
            cadr_unit=CADRUnit.m3_per_hour,
            target_ach=None,  # No user target
        )
        resp = await indoor_air_service.assess_room(req)
        assert resp.room_volume_m3 == 42.0
        assert resp.calculated_ach == 8.09
        assert resp.target_ach is None
        # Confirms NO automatic adequacy label like "Adequate for Room Size" is applied
        assert resp.filtration_assessment.target_comparison is None
        assert "Air Changes per Hour (ACH)" in resp.filtration_assessment.explanation

    @pytest.mark.anyio
    async def test_optional_target_ach_sizing(self):
        """Target comparison is evaluated ONLY when user explicitly provides target_ach."""
        req = IndoorAssessmentRequest(
            room_length_m=5.0,
            room_width_m=4.0,
            ceiling_height_m=2.5,
            has_air_purifier=True,
            cadr=250.0,
            cadr_unit=CADRUnit.m3_per_hour,
            target_ach=4.0,
        )
        resp = await indoor_air_service.assess_room(req)
        # Volume = 50.0 m³; ACH = 250 / 50 = 5.0; target = 4.0
        assert resp.room_volume_m3 == 50.0
        assert resp.calculated_ach == 5.0
        assert resp.target_ach == 4.0
        assert resp.required_cadr_m3h == 200.0
        assert resp.filtration_assessment.target_comparison is not None
        assert "meets or exceeds your selected target of 4.0 ACH" in resp.filtration_assessment.target_comparison

    @pytest.mark.anyio
    async def test_smoke_cadr_prioritized_for_fine_particles(self):
        """When smoke_cadr is supplied, it is used for sizing fine particle clearance."""
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=4.0,
            ceiling_height_m=3.0,
            has_air_purifier=True,
            cadr=300.0,
            smoke_cadr=240.0,  # Smoke CADR specified
            cadr_unit=CADRUnit.m3_per_hour,
        )
        resp = await indoor_air_service.assess_room(req)
        # Volume = 48.0 m³; ACH using smoke_cadr = 240 / 48 = 5.0
        assert resp.calculated_ach == 5.0
        assert "Smoke CADR" in resp.filtration_assessment.explanation

    @pytest.mark.anyio
    async def test_missing_cadr_returns_null_ach(self):
        """When CADR is unknown, estimated ACH must be null (no fabricated specs)."""
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=3.0,
            ceiling_height_m=2.8,
            has_air_purifier=True,
            cadr=None,
        )
        resp = await indoor_air_service.assess_room(req)
        assert resp.available_cadr_m3h is None
        assert resp.calculated_ach is None
        assert resp.filtration_assessment.purifier_status == "UNSPECIFIED_CADR"
        assert resp.filtration_assessment.target_comparison is None

    @pytest.mark.anyio
    async def test_purifier_absent_status(self):
        """When no purifier is present, calculated_ach is null and status is PURIFIER_ABSENT."""
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=3.0,
            ceiling_height_m=2.8,
            has_air_purifier=False,
        )
        resp = await indoor_air_service.assess_room(req)
        assert resp.available_cadr_m3h is None
        assert resp.calculated_ach is None
        assert resp.filtration_assessment.purifier_status == "PURIFIER_ABSENT"


# =====================================================================
# 2. FILTER MAINTENANCE & USER-REPORTED VERIFICATION
# =====================================================================

class TestPurifierMaintenanceAndVerification:
    @pytest.mark.anyio
    async def test_manufacturer_specific_filter_maintenance(self):
        """Guidance directs users to follow manufacturer instructions (no generic intervals)."""
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=4.0,
            ceiling_height_m=3.0,
            has_air_purifier=True,
            cadr=200.0,
        )
        resp = await indoor_air_service.assess_room(req)
        guidance_text = " ".join(resp.filtration_assessment.guidance).lower()
        assert "manufacturer's specific user manual" in guidance_text or "manufacturer" in guidance_text
        assert "every 2-4 weeks" not in guidance_text
        assert "every 6-12 months" not in guidance_text

    @pytest.mark.anyio
    async def test_user_reported_filter_type_flagged(self):
        """Filter type is explicitly disclosed as user self-reported, not independently verified."""
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=4.0,
            ceiling_height_m=3.0,
            has_air_purifier=True,
            cadr=200.0,
            filter_type="True HEPA H13",
        )
        resp = await indoor_air_service.assess_room(req)
        assert resp.filtration_assessment.is_user_reported_filter is True
        guidance_text = " ".join(resp.filtration_assessment.guidance).lower()
        assert "self-reported by user and has not been independently" in guidance_text

    @pytest.mark.anyio
    async def test_actual_air_cleaning_caveats_explained(self):
        """Explanation clarifies air cleaning depends on speed, filter condition, leakage, and mixing."""
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=4.0,
            ceiling_height_m=3.0,
            has_air_purifier=True,
            cadr=200.0,
        )
        resp = await indoor_air_service.assess_room(req)
        exp = resp.filtration_assessment.explanation.lower()
        assert "fan speed" in exp
        assert "filter condition" in exp
        assert "air leakage" in exp
        assert "mixing" in exp


# =====================================================================
# 3. KITCHEN VENTILATION SAFETY & COMBUSTION BACKDRAFT
# =====================================================================

class TestKitchenVentilationSafety:
    @pytest.mark.anyio
    async def test_kitchen_exhaust_backdraft_safety_warning(self):
        """Warnings and precautions must warn of combustion backdraft and room depressurization."""
        req = IndoorAssessmentRequest(
            room_length_m=4.0,
            room_width_m=4.0,
            ceiling_height_m=3.0,
            indoor_pollution_sources=["unvented_cooking"],
        )
        resp = await indoor_air_service.assess_room(req)

        # Check safety warnings list
        assert any("backdraft" in w.lower() for w in resp.warnings)
        assert any("depressuriz" in w.lower() for w in resp.warnings)

        # Check ventilation precautions
        precautions = " ".join(resp.ventilation_recommendations.precautions).lower()
        assert "backdraft" in precautions
        assert "gas geyser" in precautions or "combustion appliances" in precautions

        # Check source control action
        cooking_action = next(sc for sc in resp.source_control_recommendations if "Kitchen" in sc.source)
        assert "externally vented range hood" in cooking_action.action.lower()


# =====================================================================
# 4. CONDITION-BASED VENTILATION & SAFETY REALITY CHECKS
# =====================================================================

class TestConditionBasedVentilationAndSafety:
    @pytest.mark.anyio
    async def test_high_outdoor_pollution_ventilation(self, monkeypatch):
        """High outdoor pollution includes NCDC 12-4 PM conditional mention without safe guarantee."""
        mock_station = make_mock_outdoor_station(category="Very Poor")
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_station)

        req = IndoorAssessmentRequest(
            station_id="test_outdoor_station",
            room_length_m=4.0,
            room_width_m=4.0,
            ceiling_height_m=3.0,
        )
        resp = await indoor_air_service.assess_room(req)
        assert resp.ventilation_recommendations.outdoor_aqi_category == "Very Poor"
        assert "12 PM to 4 PM" in resp.ventilation_recommendations.guidance
        assert "not a guarantee of safe outdoor air" in resp.ventilation_recommendations.guidance

    @pytest.mark.anyio
    async def test_ozone_warning_present(self):
        """Response explicitly advises against ozone-generating air cleaners."""
        req = IndoorAssessmentRequest(room_length_m=4.0, room_width_m=4.0, ceiling_height_m=3.0)
        resp = await indoor_air_service.assess_room(req)
        assert any("OZONE SAFETY WARNING" in w for w in resp.warnings)

    @pytest.mark.anyio
    async def test_houseplant_air_cleaning_debunked(self):
        """Data limitations must state house plants cannot substitute for mechanical particle filtration."""
        req = IndoorAssessmentRequest(room_length_m=4.0, room_width_m=4.0, ceiling_height_m=3.0)
        resp = await indoor_air_service.assess_room(req)
        assert any("HOUSEPLANT REALITY CHECK" in lim for lim in resp.data_source_and_limitations)

    @pytest.mark.anyio
    async def test_no_indoor_aqi_fabrication(self):
        """Data limitations must state no exact indoor AQI claimed without physical indoor sensors."""
        req = IndoorAssessmentRequest(room_length_m=4.0, room_width_m=4.0, ceiling_height_m=3.0)
        resp = await indoor_air_service.assess_room(req)
        assert any("does not claim to know exact indoor AQI" in lim for lim in resp.data_source_and_limitations)


# =====================================================================
# 5. FASTAPI ENDPOINT INTEGRATION
# =====================================================================

class TestFastAPIAdvisorEndpoint:
    @pytest.mark.anyio
    async def test_api_indoor_assessment_endpoint(self):
        """Integration test for POST /api/v1/advisor/indoor-assessment."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "room_length_m": 4.5,
                "room_width_m": 3.8,
                "ceiling_height_m": 3.0,
                "has_air_purifier": True,
                "cadr": 350.0,
                "cadr_unit": "m3/h",
                "filter_type": "HEPA",
                "indoor_pollution_sources": ["agarbatti", "cooking"],
                "target_ach": 4.0,
                "household_budget": "medium",
            }
            resp = await client.post("/api/v1/advisor/indoor-assessment", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["room_volume_m3"] == 51.3
            assert data["available_cadr_m3h"] == 350.0
            assert data["calculated_ach"] == 6.82
            assert data["filtration_assessment"]["is_user_reported_filter"] is True
            assert "meets or exceeds your selected target" in data["filtration_assessment"]["target_comparison"]
            assert any("backdraft" in w.lower() for w in data["warnings"])
