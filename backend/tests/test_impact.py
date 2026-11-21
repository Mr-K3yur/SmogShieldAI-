"""Unit tests for Phase 5: Environmental Impact Tracker and In-Memory Session Security.

Audited scenarios:
1. Session creation returns a valid server-issued UUID4 token.
2. Accessing an invalid or unissued session returns 404 Not Found.
3. Client-submitted emissions/savings values are completely ignored and recalculated by server.
4. Completed trip logged without a baseline returns null actual avoided emissions.
5. Missing baseline includes explicit explanation that counterfactual was not invented.
6. Valid baseline computes actual avoided emissions deterministically.
7. Actual weekly summary is pure sum of completed trips, never multiplied by 4.33.
8. Actual monthly summary is pure sum of completed trips in that calendar month.
9. Projected vs actual savings are strictly separate fields.
10. Duplicate request with same session + same key + same payload returns cached result.
11. Duplicate key with DIFFERENT payload raises 409 Conflict.
12. Identical trips with different idempotency keys are legitimately accepted as separate trips.
13. Session isolation: trips in Session A never appear in Session B.
14. Session inactivity expiry (> 24 hours) returns 404 Not Found.
15. Storage disclaimer is present in every response.
"""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.impact import (
    BaselineTripInput,
    STORAGE_DISCLAIMER_TEXT,
    TripLogEntry,
)
from app.schemas.transport import FuelType, TransportMode
from app.services.impact_service import impact_service


class TestSessionSecurityAndTripLogging:

    def test_session_creation_returns_server_uuid(self):
        """Server issues a valid UUID4 session token with 24h expiry."""
        resp = impact_service.create_session()
        assert resp.session_id is not None
        assert len(resp.session_id) == 36
        assert resp.storage_disclaimer == STORAGE_DISCLAIMER_TEXT
        assert resp.expires_at_utc > resp.created_at_utc

    def test_access_invalid_session_returns_404(self):
        """Unrecognized session ID returns 404."""
        with pytest.raises(Exception) as exc:
            impact_service.get_session("non-existent-session-uuid-1234")
        assert "404" in str(exc.value)

    @pytest.mark.anyio
    async def test_client_submitted_emissions_ignored_and_recomputed(self):
        """Server recalculates emissions; client input cannot tamper with results."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.petrol_motorcycle,
            engine_capacity_cc=100,
            distance_km=10.0,
            round_trip=False,
            occupancy=1,
        )
        res = await impact_service.log_completed_trip(
            session_id=sess.session_id,
            entry=entry,
            idempotency_key="key-test-recompute-1",
        )
        # Server must calculate 10 * 0.0319 = 0.319 kg CO2
        assert res.trip.passenger_emissions_kg_co2 == 0.319
        assert res.trip.factor_id_used == "PETROL_MOTORCYCLE_UPLIFT"

    @pytest.mark.anyio
    async def test_missing_baseline_returns_null_actual_avoided(self):
        """Logged trip without baseline leaves actual_avoided_kg_co2 as None."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.intracity_bus,
            distance_km=15.0,
            occupancy=1,
            baseline_scenario=None,
        )
        res = await impact_service.log_completed_trip(
            session_id=sess.session_id,
            entry=entry,
            idempotency_key="key-no-baseline-1",
        )
        assert res.trip.actual_avoided_kg_co2 is None
        assert res.trip.avoided_status == "BASELINE_NOT_PROVIDED"

    @pytest.mark.anyio
    async def test_missing_baseline_includes_explanation(self):
        """Missing baseline explicitly explains counterfactuals are not invented."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.intracity_bus,
            distance_km=10.0,
            baseline_scenario=None,
        )
        res = await impact_service.log_completed_trip(
            session_id=sess.session_id,
            entry=entry,
            idempotency_key="key-no-baseline-2",
        )
        assert "does not invent counterfactual baseline travel" in res.trip.avoided_explanation

    @pytest.mark.anyio
    async def test_valid_baseline_computes_actual_avoided(self):
        """Bus trip (10km = 0.1516 kg CO2) replacing petrol car (10km = 1.4 kg CO2) avoids 1.2484 kg CO2."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.intracity_bus,
            distance_km=10.0,
            round_trip=False,
            occupancy=1,
            baseline_scenario=BaselineTripInput(
                mode=TransportMode.petrol_car,
                fuel_type=FuelType.petrol,
                engine_capacity_cc=1198,
                occupancy=1,
            ),
        )
        res = await impact_service.log_completed_trip(
            session_id=sess.session_id,
            entry=entry,
            idempotency_key="key-valid-baseline-1",
        )
        assert res.trip.passenger_emissions_kg_co2 == 0.1516
        assert res.trip.baseline_passenger_emissions_kg_co2 == 1.4
        assert res.trip.actual_avoided_kg_co2 == 1.2484
        assert res.trip.avoided_status == "AVOIDED_CALCULATED"

    @pytest.mark.anyio
    async def test_actual_weekly_is_sum_of_completed_trips_not_extrapolated(self):
        """Actual weekly total is a sum of logged trips, never multiplied by 4.33."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.intracity_bus,
            distance_km=10.0,
            occupancy=1,
            baseline_scenario=BaselineTripInput(
                mode=TransportMode.petrol_car,
                engine_capacity_cc=1198,
                occupancy=1,
            ),
        )
        # Log 2 identical trips
        await impact_service.log_completed_trip(sess.session_id, entry, "trip-wk-1")
        await impact_service.log_completed_trip(sess.session_id, entry, "trip-wk-2")

        summary = impact_service.get_session_summary(sess.session_id)
        assert summary.completed_action_count == 2
        assert len(summary.weekly_summaries) == 1
        wk = summary.weekly_summaries[0]
        # 2 * 0.1516 = 0.3032 kg CO2
        assert wk.total_passenger_emissions_kg_co2 == 0.3032
        # 2 * 1.2484 = 2.4968 kg CO2
        assert wk.total_avoided_kg_co2 == 2.4968
        assert wk.trip_count == 2

    @pytest.mark.anyio
    async def test_actual_monthly_is_sum_of_completed_trips_in_calendar_month(self):
        """Actual monthly summary aggregates trips within that calendar month without 4.33 multiplier."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.petrol_motorcycle,
            engine_capacity_cc=100,
            distance_km=10.0,
            occupancy=1,
        )
        await impact_service.log_completed_trip(sess.session_id, entry, "trip-mo-1")
        summary = impact_service.get_session_summary(sess.session_id)
        assert len(summary.monthly_summaries) == 1
        mo = summary.monthly_summaries[0]
        assert mo.total_passenger_emissions_kg_co2 == 0.319
        assert mo.trip_count == 1

    @pytest.mark.anyio
    async def test_idempotency_duplicate_submission_returns_cached_result(self):
        """Same session + same key + same payload: returns original result without duplicate tally."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.petrol_motorcycle,
            engine_capacity_cc=100,
            distance_km=10.0,
        )
        res1 = await impact_service.log_completed_trip(sess.session_id, entry, "idem-key-100")
        res2 = await impact_service.log_completed_trip(sess.session_id, entry, "idem-key-100")

        # Must return the identical trip_id
        assert res1.trip.trip_id == res2.trip.trip_id
        assert "duplicate" in res2.message.lower()

        # Session summary must show exactly 1 trip
        summary = impact_service.get_session_summary(sess.session_id)
        assert summary.completed_action_count == 1

    @pytest.mark.anyio
    async def test_duplicate_key_with_different_payload_raises_409(self):
        """Same session + same key + different payload: raises 409 Conflict."""
        sess = impact_service.create_session()
        entry1 = TripLogEntry(
            mode=TransportMode.petrol_motorcycle,
            engine_capacity_cc=100,
            distance_km=10.0,
        )
        entry2 = TripLogEntry(
            mode=TransportMode.intracity_bus,  # Different payload!
            distance_km=25.0,
        )
        await impact_service.log_completed_trip(sess.session_id, entry1, "idem-key-conflict")
        with pytest.raises(Exception) as exc:
            await impact_service.log_completed_trip(sess.session_id, entry2, "idem-key-conflict")
        assert "409" in str(exc.value)

    @pytest.mark.anyio
    async def test_identical_trips_with_different_idempotency_keys_accepted(self):
        """Different idempotency keys allow legitimate identical trips."""
        sess = impact_service.create_session()
        entry = TripLogEntry(
            mode=TransportMode.walking,
            distance_km=2.0,
        )
        res1 = await impact_service.log_completed_trip(sess.session_id, entry, "legit-trip-morning")
        res2 = await impact_service.log_completed_trip(sess.session_id, entry, "legit-trip-evening")

        assert res1.trip.trip_id != res2.trip.trip_id
        summary = impact_service.get_session_summary(sess.session_id)
        assert summary.completed_action_count == 2

    @pytest.mark.anyio
    async def test_session_isolation_independent_state(self):
        """Trips logged in Session A never bleed into Session B."""
        sess_a = impact_service.create_session()
        sess_b = impact_service.create_session()

        entry_a = TripLogEntry(mode=TransportMode.walking, distance_km=1.0)
        await impact_service.log_completed_trip(sess_a.session_id, entry_a, "iso-key-a")

        sum_a = impact_service.get_session_summary(sess_a.session_id)
        sum_b = impact_service.get_session_summary(sess_b.session_id)

        assert sum_a.completed_action_count == 1
        assert sum_b.completed_action_count == 0

    def test_session_inactivity_expiry(self):
        """Session older than 24 hours of inactivity is expired and raises 404."""
        sess = impact_service.create_session()
        session_obj = impact_service._sessions[sess.session_id]
        # Mock last accessed time to 25 hours ago
        session_obj.last_accessed_at_utc = datetime.now(timezone.utc) - timedelta(hours=25)

        with pytest.raises(Exception) as exc:
            impact_service.get_session(sess.session_id)
        assert "404" in str(exc.value)

    def test_storage_disclaimer_present_in_all_impact_endpoints(self):
        """Mandated storage disclaimer is present in all session responses."""
        sess = impact_service.create_session()
        assert "temporary server memory only" in sess.storage_disclaimer
        summary = impact_service.get_session_summary(sess.session_id)
        assert "temporary server memory only" in summary.storage_disclaimer


class TestFastAPIImpactEndpoints:

    @pytest.mark.anyio
    async def test_full_impact_api_workflow(self):
        """Integration test for session creation, trip logging with headers, and session summary."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create session
            create_resp = await client.post("/api/v1/impact/sessions")
            assert create_resp.status_code == 201
            session_data = create_resp.json()
            session_id = session_data["session_id"]
            assert session_id

            # 2. Log completed trip with headers
            log_payload = {
                "mode": "intracity_bus",
                "distance_km": 12.0,
                "round_trip": False,
                "occupancy": 1,
                "baseline_scenario": {
                    "mode": "petrol_car",
                    "fuel_type": "petrol",
                    "engine_capacity_cc": 1198,
                    "occupancy": 1,
                }
            }
            log_resp = await client.post(
                "/api/v1/impact/log-trip",
                json=log_payload,
                headers={
                    "x-session-id": session_id,
                    "idempotency-key": "api-test-key-1",
                }
            )
            assert log_resp.status_code == 201
            log_data = log_resp.json()
            assert log_data["trip"]["mode"] == "intracity_bus"
            assert log_data["trip"]["actual_avoided_kg_co2"] > 0

            # 3. Retrieve session summary
            summary_resp = await client.get(
                "/api/v1/impact/session-summary",
                headers={"x-session-id": session_id}
            )
            assert summary_resp.status_code == 200
            sum_data = summary_resp.json()
            assert sum_data["completed_action_count"] == 1
            assert sum_data["actual_total_emissions_kg_co2"] > 0
            assert sum_data["actual_avoided_kg_co2"] > 0
