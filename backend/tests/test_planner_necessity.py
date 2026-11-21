"""
Phase 4 — Essential vs Discretionary Activity Necessity Tests.

Verifies that planner_service.py correctly distinguishes essential travel from
discretionary activities across the Poor, Very Poor, and Severe AQI bands.

Required scenarios:
1.  Essential school commute at Poor.
2.  Essential school commute at Very Poor.
3.  Essential school commute at Severe.
4.  Essential work commute at Poor.
5.  Essential medical travel at Poor.
6.  Optional school sports (discretionary) at Poor.
7.  Discretionary outdoor play at Very Poor.
8.  Stale AQI data.
9.  Unavailable AQI data.
10. Simulated demo data.
"""

from datetime import datetime, timezone
import pytest

from app.schemas.planner import (
    ActionPriority,
    ActivityIntensity,
    ActivityNecessity,
    ActivityPlanItem,
    ActivityType,
    CommuteMethod,
    DailyPlannerRequest,
    DailyPlannerResponse,
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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mock_station(
    category: str = "Poor",
    overall_aqi: int = 260,
    is_exact: bool = True,
    lower_bound: int = 260,
    upper_bound: int = 260,
    provenance: ProvenanceType = ProvenanceType.CALCULATED,
    availability: AvailabilityType = AvailabilityType.AVAILABLE,
    freshness: FreshnessType = FreshnessType.FRESH,
    unavailable_reason: str = None,
    warnings: list = None,
) -> StationAQIResponse:
    return StationAQIResponse(
        station=StationMetadata(
            station_id="test_station_necessity",
            provider="mock",
            provider_station_id="DEL_ITO_01",
            station_name="ITO, Delhi - Test",
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


def _essential_school_commute_item() -> ActivityPlanItem:
    return ActivityPlanItem(
        activity_type=ActivityType.school_commute,
        intensity=ActivityIntensity.low,
        necessity=ActivityNecessity.essential,
        scheduled_time="08:00",
    )


def _discretionary_sports_item() -> ActivityPlanItem:
    return ActivityPlanItem(
        activity_type=ActivityType.outdoor_sports,
        intensity=ActivityIntensity.high,
        necessity=ActivityNecessity.discretionary,
        scheduled_time="15:00",
    )


def _discretionary_play_item() -> ActivityPlanItem:
    return ActivityPlanItem(
        activity_type=ActivityType.outdoor_play,
        intensity=ActivityIntensity.high,
        necessity=ActivityNecessity.discretionary,
        scheduled_time="Evening",
    )


# ===========================================================================
# Test class
# ===========================================================================

class TestEssentialVsDiscretionaryNecessity:

    # -----------------------------------------------------------------------
    # Scenario 1: Essential school commute — Poor
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_essential_school_commute_poor_proceeds(self, monkeypatch):
        """Essential school commute at Poor AQI must NOT be cancelled; must give exposure-min guidance."""
        mock = _mock_station(category="Poor", overall_aqi=260)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(
            station_id="test_station_necessity",
            has_children=True,
            commute_method=CommuteMethod.work_from_home,
            planned_activities=[_essential_school_commute_item()],
        )
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        school_recs = [r for r in resp.recommendations if r.activity_type == "school_commute"]
        assert len(school_recs) == 1
        rec = school_recs[0]

        # Must NOT tell family to stay home / cancel commute
        assert "remain indoors" not in rec.recommendation.lower()
        assert "cancel" not in rec.recommendation.lower()

        # Must indicate commute can proceed
        assert "essential" in rec.recommendation.lower() or "proceed" in rec.recommendation.lower()

        # Must include optional mask wording (not mandatory)
        all_steps = " ".join(rec.practical_steps).lower()
        assert "optional" in all_steps or "optional" in rec.recommendation.lower()
        assert "mandatory" not in all_steps

        # Must mention transit alternatives
        assert any(
            kw in step.lower()
            for step in rec.practical_steps
            for kw in ["bus", "metro", "carpool", "transit"]
        )

    # -----------------------------------------------------------------------
    # Scenario 2: Essential school commute — Very Poor
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_essential_school_commute_very_poor_proceeds(self, monkeypatch):
        """Essential school commute at Very Poor AQI must NOT be cancelled; strict exposure-min guidance."""
        mock = _mock_station(category="Very Poor", overall_aqi=340)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(
            station_id="test_station_necessity",
            has_children=True,
            commute_method=CommuteMethod.work_from_home,
            planned_activities=[_essential_school_commute_item()],
        )
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        school_recs = [r for r in resp.recommendations if r.activity_type == "school_commute"]
        assert len(school_recs) == 1
        rec = school_recs[0]

        # Must NOT cancel / mandate stay at home
        assert "remain indoors" not in rec.recommendation.lower()
        assert "cancel" not in rec.recommendation.lower()

        # Must reference essential or proceed
        assert "essential" in rec.recommendation.lower() or "proceed" in rec.recommendation.lower()

        # Mask guidance must be optional
        all_steps = " ".join(rec.practical_steps).lower()
        assert "optional" in all_steps or "optional" in rec.recommendation.lower()
        assert "mandatory" not in all_steps

    # -----------------------------------------------------------------------
    # Scenario 3: Essential school commute — Severe
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_essential_school_commute_severe_proceeds(self, monkeypatch):
        """Essential school commute at Severe AQI must NOT be cancelled; strict minimisation guidance."""
        mock = _mock_station(
            category="Severe",
            overall_aqi=None,
            is_exact=False,
            lower_bound=401,
            upper_bound=500,
        )
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(
            station_id="test_station_necessity",
            has_children=True,
            commute_method=CommuteMethod.work_from_home,
            planned_activities=[_essential_school_commute_item()],
        )
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        school_recs = [r for r in resp.recommendations if r.activity_type == "school_commute"]
        assert len(school_recs) == 1
        rec = school_recs[0]

        # Must NOT cancel / mandate stay home
        assert "remain indoors" not in rec.recommendation.lower()
        assert "cancel" not in rec.recommendation.lower()

        # Must indicate essential / proceed
        assert "essential" in rec.recommendation.lower() or "proceed" in rec.recommendation.lower()

        # Exposure-minimisation steps present
        all_steps = " ".join(rec.practical_steps).lower()
        assert any(kw in all_steps for kw in ["minimise", "minimize", "reduce", "enclosed", "transit"])

    # -----------------------------------------------------------------------
    # Scenario 4: Essential work commute — Poor
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_essential_work_commute_poor_proceeds(self, monkeypatch):
        """Essential work commute at Poor AQI must NOT be cancelled; exposure-minimisation guidance."""
        mock = _mock_station(category="Poor", overall_aqi=255)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(
            station_id="test_station_necessity",
            commute_method=CommuteMethod.metro,
            planned_activities=[
                ActivityPlanItem(
                    activity_type=ActivityType.work_commute,
                    intensity=ActivityIntensity.low,
                    necessity=ActivityNecessity.essential,
                    scheduled_time="09:00",
                )
            ],
        )
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        work_recs = [r for r in resp.recommendations if r.activity_type == "work_commute"]
        assert len(work_recs) == 1
        rec = work_recs[0]

        # Must NOT cancel travel
        assert "remain indoors" not in rec.recommendation.lower()
        assert "cancel" not in rec.recommendation.lower()

        # Must indicate proceed / essential
        assert "essential" in rec.recommendation.lower() or "proceed" in rec.recommendation.lower()

    # -----------------------------------------------------------------------
    # Scenario 5: Essential medical travel — Poor
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_essential_medical_travel_poor_proceeds(self, monkeypatch):
        """Essential medical travel at Poor AQI must NOT be cancelled; minimisation guidance only."""
        mock = _mock_station(category="Poor", overall_aqi=270)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(
            station_id="test_station_necessity",
            has_sensitive_member=True,
            commute_method=CommuteMethod.work_from_home,
            planned_activities=[
                ActivityPlanItem(
                    activity_type=ActivityType.essential_medical_travel,
                    intensity=ActivityIntensity.low,
                    necessity=ActivityNecessity.essential,
                )
            ],
        )
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        medical_recs = [r for r in resp.recommendations if r.activity_type == "essential_medical_travel"]
        assert len(medical_recs) == 1
        rec = medical_recs[0]

        # Must NOT cancel / mandate stay home
        assert "remain indoors" not in rec.recommendation.lower()
        assert "cancel" not in rec.recommendation.lower()

        # Must indicate proceed / essential
        assert "essential" in rec.recommendation.lower() or "proceed" in rec.recommendation.lower()

    # -----------------------------------------------------------------------
    # Scenario 6: Discretionary outdoor school sports — Poor
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_discretionary_school_sports_poor_avoided(self, monkeypatch):
        """Discretionary outdoor school sports at Poor AQI must be advised to be avoided or moved indoors (NCDC 2025)."""
        mock = _mock_station(category="Poor", overall_aqi=255)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(
            station_id="test_station_necessity",
            has_children=True,
            commute_method=CommuteMethod.work_from_home,
            planned_activities=[_discretionary_sports_item()],
        )
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        sports_recs = [r for r in resp.recommendations if r.activity_type == "outdoor_sports"]
        assert len(sports_recs) == 1
        rec = sports_recs[0]

        # Must NOT return "Essential Travel Guidance" for a discretionary activity
        assert "essential travel guidance" not in rec.action.lower()

        # Must advise avoidance / limitation for discretionary Poor-air activity
        assert any(
            kw in (rec.action + rec.recommendation).lower()
            for kw in ["avoid", "postpone", "reduce", "indoor", "limit"]
        )

    # -----------------------------------------------------------------------
    # Scenario 7: Discretionary outdoor play — Very Poor
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_discretionary_outdoor_play_very_poor_avoided(self, monkeypatch):
        """Discretionary outdoor play at Very Poor AQI must be advised against for general population."""
        mock = _mock_station(category="Very Poor", overall_aqi=340)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(
            station_id="test_station_necessity",
            commute_method=CommuteMethod.work_from_home,
            planned_activities=[_discretionary_play_item()],
        )
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        play_recs = [r for r in resp.recommendations if r.activity_type == "outdoor_play"]
        assert len(play_recs) == 1
        rec = play_recs[0]

        # Must NOT return "Essential Travel" action
        assert "essential travel" not in rec.action.lower()

        # Must advise avoidance
        assert any(
            kw in (rec.action + rec.recommendation).lower()
            for kw in ["avoid", "remain indoors", "indoor"]
        )

    # -----------------------------------------------------------------------
    # Scenario 8: Stale AQI data
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_stale_aqi_data_warnings_present(self, monkeypatch):
        """With stale data, response must include staleness warning and time-specific guidance is withheld."""
        mock = _mock_station(category="Poor", overall_aqi=260, freshness=FreshnessType.STALE)
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(station_id="test_station_necessity")
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        # Staleness warning must be present
        assert any("stale" in w.lower() or "STALE" in w for w in resp.warnings)

        # Time-specific optimization must be withheld for Poor + stale
        assert resp.conditional_timing_guidance is not None
        assert "stale_timing_disclaimer" in resp.conditional_timing_guidance

    # -----------------------------------------------------------------------
    # Scenario 9: Unavailable AQI data
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_unavailable_aqi_data_safe_fallback(self, monkeypatch):
        """With UNAVAILABLE AQI, response must suspend AQI-dependent scheduling and provide baseline precaution."""
        mock = _mock_station(
            category="Unknown",
            overall_aqi=None,
            is_exact=False,
            lower_bound=None,
            upper_bound=None,
            availability=AvailabilityType.UNAVAILABLE,
            unavailable_reason="No live data available from provider.",
        )
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(station_id="test_station_necessity")
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        # Fallback action priority
        assert resp.action_priority == ActionPriority.MODERATE

        # Must mention unavailable / suspended scheduling
        assert any(
            kw in resp.public_health_summary.upper()
            for kw in ["UNAVAILABLE", "EXPIRED", "SUSPENDED"]
        )

        # At least one baseline precaution recommendation
        assert len(resp.recommendations) >= 1
        assert any(
            "precaution" in r.action.lower() or "baseline" in r.action.lower() or "general" in r.action.lower()
            for r in resp.recommendations
        )

        # Must warn about unavailable data
        assert any("AQI-DEPENDENT" in w or "unavailable" in w.lower() for w in resp.warnings)

    # -----------------------------------------------------------------------
    # Scenario 10: Simulated demo data
    # -----------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_simulated_demo_data_warning_present(self, monkeypatch):
        """With SIMULATED_DEMO provenance, response must include demo-mode warning."""
        mock = _mock_station(
            category="Poor",
            overall_aqi=260,
            provenance=ProvenanceType.SIMULATED_DEMO,
            freshness=FreshnessType.FRESH,
        )
        monkeypatch.setattr(station_service, "get_station_aqi", lambda sid: mock)

        req = DailyPlannerRequest(station_id="test_station_necessity")
        resp: DailyPlannerResponse = await planner_service.generate_plan(req)

        # Must include demo-mode warning
        assert any(
            "demo" in w.lower() or "simulated" in w.lower()
            for w in resp.warnings
        )

        # AQI context must report SIMULATED_DEMO provenance
        assert resp.aqi_context.provenance == "SIMULATED_DEMO"
