"""In-memory Impact Tracker Service with Session Security and Idempotency Protection.

Enforces:
- Server-generated UUID4 session bearer tokens
- Session isolation in a single process memory dict (with multi-worker disclaimer)
- 24-hour inactivity session expiry
- Idempotency key duplicate protection:
    - Same session + same key + same payload: return cached result without duplicate log
    - Same session + same key + different payload: raise 409 Conflict
    - Different keys: allow legitimate identical trips
- 100% server-side recomputation of trip emissions (zero trust of client values)
- Baseline scenario requirement for actual avoided emissions (no counterfactual invention)
- Strict separation of actual completed trip totals from projected savings
- Actual weekly and monthly totals are pure sums of completed trips (never extrapolated by 4.33)
"""

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Dict, List, Optional
import uuid
from fastapi import HTTPException, status

from app.schemas.impact import (
    CompletedTripRecord,
    ImpactSessionSummary,
    MonthlyActualSummary,
    SessionCreationResponse,
    STORAGE_DISCLAIMER_TEXT,
    TripLogEntry,
    TripLogResult,
    WeeklyActualSummary,
)
from app.services.station_service import station_service
from app.services.transport_service import transport_service

logger = logging.getLogger(__name__)


class SessionData:
    """Internal container for an individual isolated session."""
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        now = datetime.now(timezone.utc)
        self.created_at_utc: datetime = now
        self.last_accessed_at_utc: datetime = now
        self.trips: List[CompletedTripRecord] = []
        # Map: idempotency_key -> (payload_hash_or_dump, CompletedTripRecord)
        self.idempotency_cache: Dict[str, tuple[str, CompletedTripRecord]] = {}

    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check whether session has lapsed after 24 hours of inactivity."""
        return (datetime.now(timezone.utc) - self.last_accessed_at_utc) > timedelta(hours=max_age_hours)

    def touch(self):
        """Update last access timestamp."""
        self.last_accessed_at_utc = datetime.now(timezone.utc)


class ImpactService:
    """In-memory session manager and impact tracker."""

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}

    def _prune_expired_sessions(self):
        """Lazy pruning of sessions exceeding 24 hours of inactivity."""
        expired_ids = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired_ids:
            del self._sessions[sid]

    def create_session(self) -> SessionCreationResponse:
        """Issue a new server-generated UUID4 session token."""
        self._prune_expired_sessions()
        session_id = str(uuid.uuid4())
        session = SessionData(session_id)
        self._sessions[session_id] = session
        now = session.created_at_utc
        expires_at = now + timedelta(hours=24)

        return SessionCreationResponse(
            session_id=session_id,
            created_at_utc=now,
            expires_at_utc=expires_at,
            storage_disclaimer=STORAGE_DISCLAIMER_TEXT,
        )

    def get_session(self, session_id: str) -> SessionData:
        """Retrieve and validate session; raises 404 if invalid or expired."""
        self._prune_expired_sessions()
        session = self._sessions.get(session_id)
        if not session or session.is_expired():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or has expired after 24 hours of inactivity."
            )
        session.touch()
        return session

    async def log_completed_trip(
        self,
        session_id: str,
        entry: TripLogEntry,
        idempotency_key: str,
    ) -> TripLogResult:
        """Deterministically record a completed trip with idempotency protection and server calculation."""
        session = self.get_session(session_id)

        # Normalize payload for idempotency verification
        payload_dump = entry.model_dump_json()

        # Idempotency checks
        if idempotency_key in session.idempotency_cache:
            cached_payload, cached_record = session.idempotency_cache[idempotency_key]
            if cached_payload == payload_dump:
                # Same session + same key + same payload: return original result without duplicate log
                return TripLogResult(
                    session_id=session_id,
                    trip=cached_record,
                    storage_disclaimer=STORAGE_DISCLAIMER_TEXT,
                    message="Idempotent duplicate request recognized. Original trip record returned without duplicate tally.",
                )
            else:
                # Same session + same key + different payload: raise 409 Conflict
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key collision: a different payload was previously submitted with this key in this session."
                )

        # 1. Server-side AQI context resolution (never trust client-submitted data as verified)
        aqi_category: Optional[str] = None
        aqi_source = "NONE"

        if entry.station_id:
            try:
                raw_st = station_service.get_station_aqi(entry.station_id)
                station_data = await raw_st if hasattr(raw_st, "__await__") else raw_st
                aqi_category = station_data.category
                aqi_source = "SERVER_VERIFIED"
            except Exception as e:
                logger.warning(f"Could not fetch server-side AQI for station '{entry.station_id}': {e}")

        if not aqi_category and entry.user_reported_aqi_category:
            aqi_category = entry.user_reported_aqi_category
            aqi_source = "USER_REPORTED"

        # 2. Server-side completed trip emission calculation
        trip_calc = transport_service.calculate_mode_emissions(
            mode=entry.mode,
            distance_km=entry.distance_km,
            round_trip=entry.round_trip,
            occupancy=entry.occupancy,
            fuel_type=entry.fuel_type,
            engine_capacity_cc=entry.engine_capacity_cc,
            user_ev_kwh_per_km=entry.user_ev_kwh_per_km,
            user_metro_kwh_per_pax_km=entry.user_metro_kwh_per_pax_km,
            aqi_category=aqi_category or "Unknown",
        )

        if not trip_calc.is_available or trip_calc.passenger_emissions_kg_co2 is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to calculate emissions for completed trip: {trip_calc.unavailable_reason or 'Factor unavailable.'}"
            )

        actual_emissions = trip_calc.passenger_emissions_kg_co2
        effective_dist = trip_calc.effective_distance_km

        # 3. Server-side actual avoided emissions calculation via explicit baseline
        actual_avoided: Optional[float] = None
        baseline_emissions: Optional[float] = None
        baseline_mode = None
        avoided_status_str = "BASELINE_NOT_PROVIDED"
        avoided_explanation = (
            "Actual avoided emissions cannot be calculated because a documented baseline commute scenario "
            "was not provided. SmogShield AI does not invent counterfactual baseline travel."
        )

        if entry.baseline_scenario:
            base_input = entry.baseline_scenario
            baseline_mode = base_input.mode
            base_calc = transport_service.calculate_mode_emissions(
                mode=base_input.mode,
                distance_km=entry.distance_km,
                round_trip=entry.round_trip,
                occupancy=base_input.occupancy,
                fuel_type=base_input.fuel_type,
                engine_capacity_cc=base_input.engine_capacity_cc,
                user_ev_kwh_per_km=base_input.user_ev_kwh_per_km,
                user_metro_kwh_per_pax_km=base_input.user_metro_kwh_per_pax_km,
                aqi_category=aqi_category or "Unknown",
            )
            if base_calc.is_available and base_calc.passenger_emissions_kg_co2 is not None:
                baseline_emissions = base_calc.passenger_emissions_kg_co2
                actual_avoided = round(baseline_emissions - actual_emissions, 4)
                if actual_avoided < 0.0:
                    avoided_status_str = "EMISSIONS_INCREASE"
                    avoided_explanation = (
                        f"Completed trip resulted in an estimated emissions INCREASE of {abs(actual_avoided)} kg CO2 "
                        f"compared to baseline {base_input.mode.value.replace('_', ' ')}."
                    )
                else:
                    avoided_status_str = "AVOIDED_CALCULATED"
                    avoided_explanation = (
                        f"Successfully avoided an estimated {actual_avoided} kg CO2 compared to baseline "
                        f"{base_input.mode.value.replace('_', ' ')}."
                    )
            else:
                avoided_status_str = "BASELINE_FACTOR_UNAVAILABLE"
                avoided_explanation = f"Baseline comparison could not be calculated: {base_calc.unavailable_reason}."

        trip_record = CompletedTripRecord(
            trip_id=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            logged_at_utc=datetime.now(timezone.utc),
            mode=entry.mode,
            effective_distance_km=effective_dist,
            round_trip=entry.round_trip,
            occupancy=entry.occupancy,
            passenger_emissions_kg_co2=actual_emissions,
            factor_id_used=trip_calc.factor_id_used or "UNKNOWN",
            factor_status=trip_calc.factor_status.value if trip_calc.factor_status else "UNKNOWN",
            baseline_mode=baseline_mode,
            baseline_passenger_emissions_kg_co2=baseline_emissions,
            actual_avoided_kg_co2=actual_avoided,
            avoided_status=avoided_status_str,
            avoided_explanation=avoided_explanation,
            aqi_context_source=aqi_source,
            aqi_category=aqi_category,
            notes=entry.notes,
        )

        session.trips.append(trip_record)
        session.idempotency_cache[idempotency_key] = (payload_dump, trip_record)

        return TripLogResult(
            session_id=session_id,
            trip=trip_record,
            storage_disclaimer=STORAGE_DISCLAIMER_TEXT,
            message="Completed trip successfully recorded and audited by server.",
        )

    def get_session_summary(self, session_id: str) -> ImpactSessionSummary:
        """Compute comprehensive in-memory session summary from actual completed trips."""
        session = self.get_session(session_id)

        trips = session.trips
        action_count = len(trips)
        total_emissions = round(sum(t.passenger_emissions_kg_co2 for t in trips), 4)

        # Actual avoided emissions (only summing trips where baseline was provided)
        actual_avoided_sum = round(sum(t.actual_avoided_kg_co2 for t in trips if t.actual_avoided_kg_co2 is not None), 4)
        no_baseline_count = sum(1 for t in trips if t.actual_avoided_kg_co2 is None)

        # Emissions breakdown by mode
        by_mode: Dict[str, float] = {}
        for t in trips:
            m = t.mode.value
            by_mode[m] = round(by_mode.get(m, 0.0) + t.passenger_emissions_kg_co2, 4)

        # Weekly summaries (ISO week) — NEVER multiplied by 4.33
        weekly_map: Dict[tuple[int, int], List[CompletedTripRecord]] = {}
        for t in trips:
            iso_year, iso_week, _ = t.logged_at_utc.isocalendar()
            weekly_map.setdefault((iso_year, iso_week), []).append(t)

        weekly_summaries: List[WeeklyActualSummary] = []
        for (y, w), w_trips in sorted(weekly_map.items()):
            w_emissions = round(sum(t.passenger_emissions_kg_co2 for t in w_trips), 4)
            w_avoided = round(sum(t.actual_avoided_kg_co2 for t in w_trips if t.actual_avoided_kg_co2 is not None), 4)
            w_inc = sum(1 for t in w_trips if (t.actual_avoided_kg_co2 or 0.0) < 0.0)
            weekly_summaries.append(
                WeeklyActualSummary(
                    iso_year=y,
                    iso_week=w,
                    trip_count=len(w_trips),
                    total_passenger_emissions_kg_co2=w_emissions,
                    total_avoided_kg_co2=w_avoided,
                    emissions_increase_trips=w_inc,
                )
            )

        # Monthly summaries (calendar month) — NEVER extrapolated from weekly
        monthly_map: Dict[tuple[int, int], List[CompletedTripRecord]] = {}
        for t in trips:
            monthly_map.setdefault((t.logged_at_utc.year, t.logged_at_utc.month), []).append(t)

        monthly_summaries: List[MonthlyActualSummary] = []
        for (y, m), m_trips in sorted(monthly_map.items()):
            m_emissions = round(sum(t.passenger_emissions_kg_co2 for t in m_trips), 4)
            m_avoided = round(sum(t.actual_avoided_kg_co2 for t in m_trips if t.actual_avoided_kg_co2 is not None), 4)
            m_inc = sum(1 for t in m_trips if (t.actual_avoided_kg_co2 or 0.0) < 0.0)
            monthly_summaries.append(
                MonthlyActualSummary(
                    year=y,
                    month=m,
                    trip_count=len(m_trips),
                    total_passenger_emissions_kg_co2=m_emissions,
                    total_avoided_kg_co2=m_avoided,
                    emissions_increase_trips=m_inc,
                )
            )

        expires_at = session.last_accessed_at_utc + timedelta(hours=24)

        return ImpactSessionSummary(
            session_id=session.session_id,
            created_at_utc=session.created_at_utc,
            last_accessed_at_utc=session.last_accessed_at_utc,
            expires_at_utc=expires_at,
            storage_disclaimer=STORAGE_DISCLAIMER_TEXT,
            completed_action_count=action_count,
            actual_total_emissions_kg_co2=total_emissions,
            actual_avoided_kg_co2=actual_avoided_sum,
            trips_without_baseline_count=no_baseline_count,
            emissions_by_mode=by_mode,
            weekly_summaries=weekly_summaries,
            monthly_summaries=monthly_summaries,
            completed_trips=trips,
        )


impact_service = ImpactService()
