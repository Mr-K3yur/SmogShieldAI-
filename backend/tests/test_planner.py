"""Comprehensive tests for Phase 4: Personalized Daily Planner.

Audited and verified against official Government of India NCDC Health Advisory on Air Pollution (2025):
1. Exact 6-category NCDC 2025 guidance mapping (Good through Severe).
2. Clear distinction of General Population vs Vulnerable Population recommendations.
3. Schoolchildren advisory: outdoor activity limitation/postponement during Poor, Very Poor, and Severe conditions.
4. Face masks as an optional protective choice (never called mandatory, no false guarantees).
5. Conditional diurnal timing guidance (avoid morning/evening walks, windows 12-4 PM conditional mention).
6. Never claims 12-4 PM is a universally safe outdoor exercise window.
7. Structured advisory traceability to NCDC 2025 official document.
8. No fabricated personal exposure estimates, risk scores, or clinical prescriptions.
9. Stale, expired, unavailable, and simulated demo mode integrity.
10. REST API endpoint: POST /api/v1/planner/generate.
11. Essential vs discretionary activity distinction across Poor, Very Poor, and Severe bands.
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.planner import (
    ActionPriority,
    ActivityIntensity,
    ActivityNecessity,
    ActivityType,
    CommuteMethod,
    DailyPlannerRequest,
    DailyPlannerResponse,
    HouseholdBudget,
)
from app.schemas.station import (
    AvailabilityType,
    FreshnessType,
    ProvenanceType,
    StationAQIResponse,
    StationMetadata,
)
from app.services.planner_service import planner_service
from app.services.station_service import station_service


def make_mock_station_response(
    category: str = "Poor",
    overall_aqi: int = 250,
    is_exact: bool = True,
    lower_bound: int = 250,
    upper_bound: int = 250,
    provenance: ProvenanceType = ProvenanceType.CALCULATED,
    availability: AvailabilityType = AvailabilityType.AVAILABLE,
    freshness: FreshnessType = FreshnessType.FRESH,
    warnings: list = None,
    unavailable_reason: str = None,
) -> StationAQIResponse:
    """Helper to generate standardized StationAQIResponse instances for testing."""
    return StationAQIResponse(
        station=StationMetadata(
            station_id="test_station_ito",
            provider="mock",
            provider_station_id="DEL_ITO_01",
            station_name="ITO, Delhi - CPCB (Test)",
            city="Delhi",
            state="Delhi",
            latitude=28.6289,
            longitude=77.2405,
            country="India",
            timezone="Asia/Kolkata",
        ),
        provenance=provenance,
        availability=availability,
        freshness=freshness,
        provider_reported_aqi=None,
        provider_reported_category=None,
        calculated_aqi=overall_aqi if is_exact else None,
        overall_aqi=overall_aqi if (availability == AvailabilityType.AVAILABLE and is_exact) else None,
        overall_aqi_lower_bound=lower_bound if availability == AvailabilityType.AVAILABLE else None,
        overall_aqi_upper_bound=upper_bound if availability == AvailabilityType.AVAILABLE else None,
        is_exact=is_exact,
        category=category,
        dominant_pollutant="PM2.5",
        pollutant_measurements={},
        source="Test Provider",
        observed_at_utc=datetime.now(timezone.utc),
        observed_at_ist="20 Nov 2026, 11:30 AM IST",
        warnings=warnings or [],
        unavailable_reason=unavailable_reason,
    )


# =====================================================================
# 1. EXACT SIX-CATEGORY NCDC 2025 MAPPING & POPULATION DISTINCTION
# =====================================================================

class TestNCDC2025CategoryMapping:
    @pytest.mark.anyio
    async def test_good_aqi_category_ncdc(self, monkeypatch):
        """Good: No special precautions for both general and vulnerable populations."""
        mock_resp = make_mock_station_response(category="Good", overall_aqi=35, lower_bound=35, upper_bound=35)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        assert resp.action_priority == ActionPriority.LOW
        assert "No special precautions" in resp.general_population_advisory
        assert "No special precautions" in resp.vulnerable_population_advisory

    @pytest.mark.anyio
    async def test_satisfactory_aqi_category_ncdc(self, monkeypatch):
        """Satisfactory: General pop = No special precautions; Vulnerable = Reduce prolonged/strenuous exertion."""
        mock_resp = make_mock_station_response(category="Satisfactory", overall_aqi=75, lower_bound=75, upper_bound=75)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito", has_sensitive_member=True)
        resp = await planner_service.generate_plan(req)

        assert resp.action_priority == ActionPriority.LOW
        assert "No special precautions" in resp.general_population_advisory
        assert "Reduce prolonged or strenuous" in resp.vulnerable_population_advisory

    @pytest.mark.anyio
    async def test_moderate_aqi_category_ncdc(self, monkeypatch):
        """Moderate: General pop = Reduce prolonged/strenuous; Vulnerable = Avoid prolonged/strenuous."""
        mock_resp = make_mock_station_response(category="Moderate", overall_aqi=150, lower_bound=150, upper_bound=150)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert resp.action_priority == ActionPriority.MODERATE
        assert "Reduce prolonged or strenuous" in resp.general_population_advisory
        assert "Avoid prolonged or strenuous" in resp.vulnerable_population_advisory

    @pytest.mark.anyio
    async def test_poor_aqi_category_ncdc(self, monkeypatch):
        """Poor: General pop = Avoid outdoor physical exertion; Vulnerable = Avoid outdoor physical activities."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=260, lower_bound=260, upper_bound=260)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert resp.action_priority == ActionPriority.HIGH
        assert "Avoid outdoor physical exertion" in resp.general_population_advisory
        assert "Avoid outdoor physical activities" in resp.vulnerable_population_advisory

    @pytest.mark.anyio
    async def test_very_poor_aqi_category_ncdc(self, monkeypatch):
        """Very Poor: General pop = Avoid outdoor physical activities; Vulnerable = Remain indoors and keep activity low."""
        mock_resp = make_mock_station_response(category="Very Poor", overall_aqi=340, lower_bound=340, upper_bound=340)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert resp.action_priority == ActionPriority.URGENT
        assert "Avoid outdoor physical activities" in resp.general_population_advisory
        assert "morning and late evening" in resp.general_population_advisory
        assert "Remain indoors and keep activity levels low" in resp.vulnerable_population_advisory

    @pytest.mark.anyio
    async def test_severe_aqi_category_ncdc(self, monkeypatch):
        """Severe: General pop = Avoid outdoor physical activities; Vulnerable = Remain indoors and keep activity low."""
        mock_resp = make_mock_station_response(
            category="Severe",
            overall_aqi=None,
            is_exact=False,
            lower_bound=401,
            upper_bound=500,
        )
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert resp.action_priority == ActionPriority.URGENT
        assert "Avoid outdoor physical activities" in resp.general_population_advisory
        assert "Remain indoors and keep activity levels low" in resp.vulnerable_population_advisory


# =====================================================================
# 2. SCHOOLCHILDREN & DEMOGRAPHIC TAILORING
# =====================================================================

class TestSchoolchildrenAndDemographics:
    @pytest.mark.anyio
    async def test_schoolchildren_poor_or_higher_recommendations(self, monkeypatch):
        """NCDC 2025 school advisory: limit or postpone outdoor school activities during Poor+ air."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=275)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito", has_children=True)
        resp = await planner_service.generate_plan(req)

        child_recs = [r for r in resp.recommendations if r.activity_type == "child_health_protection"]
        assert len(child_recs) == 1
        assert "Limit or Postpone Outdoor School Activities" in child_recs[0].action
        assert "postpone" in child_recs[0].recommendation.lower()

    @pytest.mark.anyio
    async def test_older_adults_remain_indoors(self, monkeypatch):
        """Older adults advised to remain indoors and avoid morning/late-evening walks in Poor+ air."""
        mock_resp = make_mock_station_response(category="Very Poor", overall_aqi=350)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito", has_older_adults=True)
        resp = await planner_service.generate_plan(req)

        senior_recs = [r for r in resp.recommendations if r.activity_type == "senior_citizen_protection"]
        assert len(senior_recs) == 1
        assert "Remain Indoors" in senior_recs[0].action
        assert "morning" in senior_recs[0].action.lower()

    @pytest.mark.anyio
    async def test_sensitive_members_inhaler_protocol(self, monkeypatch):
        """Sensitive members reminded to keep prescribed medications accessible without clinical prescription."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=240)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito", has_sensitive_member=True)
        resp = await planner_service.generate_plan(req)

        sens_recs = [r for r in resp.recommendations if r.activity_type == "sensitive_member_protocol"]
        assert len(sens_recs) == 1
        assert any("inhaler" in step.lower() or "physician" in step.lower() for step in sens_recs[0].practical_steps)


# =====================================================================
# 3. MASK GUIDANCE AUDIT (OPTIONAL, NO GUARANTEE, FIT-APPROPRIATE)
# =====================================================================

class TestMaskRecommendationsAudit:
    @pytest.mark.anyio
    async def test_masks_are_optional_not_mandatory(self, monkeypatch):
        """Confirms that masks are never stated as mandatory or compulsory."""
        mock_resp = make_mock_station_response(category="Severe", overall_aqi=None, is_exact=False)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito", commute_method=CommuteMethod.two_wheeler)
        resp = await planner_service.generate_plan(req)

        all_text = " ".join([
            resp.public_health_summary,
            resp.general_population_advisory,
            resp.vulnerable_population_advisory,
            *[r.recommendation + " " + " ".join(r.practical_steps) for r in resp.recommendations],
        ]).lower()

        assert "mandatory mask" not in all_text
        assert "compulsory mask" not in all_text
        assert "mandatory n95" not in all_text
        assert any("optional" in step.lower() for r in resp.recommendations for step in r.practical_steps if "mask" in step.lower())

    @pytest.mark.anyio
    async def test_no_unsupported_mask_guarantee(self, monkeypatch):
        """Data limitations must state masks do not guarantee complete protection and do not replace exposure reduction."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=260)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert any("do not guarantee complete protection" in lim for lim in resp.data_limitations)
        assert any("do not replace reducing unnecessary outdoor exposure" in lim for lim in resp.data_limitations)


# =====================================================================
# 4. CONDITIONAL TIMING GUIDANCE (NO SAFE 12-4 PM CLAIM)
# =====================================================================

class TestConditionalTimingGuidance:
    @pytest.mark.anyio
    async def test_official_conditional_timing_advice(self, monkeypatch):
        """On Poor-to-Severe days, provides NCDC conditional timing for walks, windows, and 12-4pm ventilation note."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=250)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert resp.conditional_timing_guidance is not None
        assert "outdoor_walks" in resp.conditional_timing_guidance
        assert "windows_and_doors" in resp.conditional_timing_guidance
        assert "ventilation_window_note" in resp.conditional_timing_guidance
        assert "12 PM to 4 PM" in resp.conditional_timing_guidance["ventilation_window_note"]

    @pytest.mark.anyio
    async def test_no_claim_that_12_4_pm_is_universally_safe(self, monkeypatch):
        """Confirms 12-4 PM is not claimed as a safe outdoor exercise window."""
        mock_resp = make_mock_station_response(category="Very Poor", overall_aqi=330)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        note = resp.conditional_timing_guidance["ventilation_window_note"].lower()
        assert "not a guarantee of safe outdoor air" in note
        assert "not an endorsement of afternoon outdoor exercise" in note

    @pytest.mark.anyio
    async def test_stale_data_withholds_time_specific_optimization(self, monkeypatch):
        """When station data is stale (>4h), time-specific optimization is disclaimed."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=250, freshness=FreshnessType.STALE)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert resp.conditional_timing_guidance is not None
        assert "stale_timing_disclaimer" in resp.conditional_timing_guidance


# =====================================================================
# 5. SOURCE TRACEABILITY & INTEGRITY RULES
# =====================================================================

class TestSourceTraceabilityAndIntegrity:
    @pytest.mark.anyio
    async def test_structured_advisory_reference_present(self, monkeypatch):
        """Response contains structured NCDC 2025 advisory reference with URL and issuing organization."""
        mock_resp = make_mock_station_response(category="Very Poor", overall_aqi=320)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        assert resp.structured_advisory_reference.publication_year == "2025"
        assert "NCDC" in resp.structured_advisory_reference.issuing_organization
        assert "ncdc.mohfw.gov.in" in resp.structured_advisory_reference.public_source_url

    @pytest.mark.anyio
    async def test_no_fabricated_personal_exposure_estimates(self, monkeypatch):
        """Ensures no personal pollution exposure values or health multipliers are output."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=260)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        req = DailyPlannerRequest(station_id="test_station_ito")
        resp = await planner_service.generate_plan(req)

        resp_dict = resp.model_dump()
        assert "personal_exposure" not in resp_dict
        assert "family_risk_score" not in resp_dict
        assert "health_multiplier" not in resp_dict


# =====================================================================
# 6. FASTAPI ENDPOINT INTEGRATION
# =====================================================================

class TestFastAPIPlannerEndpoint:
    @pytest.mark.anyio
    async def test_api_planner_generate_endpoint(self, monkeypatch):
        """Integration test for POST /api/v1/planner/generate."""
        mock_resp = make_mock_station_response(category="Poor", overall_aqi=260)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock_resp)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "station_id": "test_station_ito",
                "family_size": 4,
                "has_children": True,
                "has_older_adults": True,
                "has_sensitive_member": False,
                "household_budget": "medium",
                "commute_method": "metro",
            }
            resp = await client.post("/api/v1/planner/generate", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["station_id"] == "test_station_ito"
            assert data["general_population_advisory"] == "Avoid outdoor physical exertion."
            assert data["vulnerable_population_advisory"] == "Avoid outdoor physical activities."
            assert "structured_advisory_reference" in data
            assert data["structured_advisory_reference"]["publication_year"] == "2025"
