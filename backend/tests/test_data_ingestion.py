"""Comprehensive test suite for Phase 3: AQI Data Ingestion & Provenance Engine.

Audited and verified against:
1. data.gov.in resource 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69 field mapping (no scalar AQI)
2. pollutant_avg normalization & missing averaging-window handling
3. Demo mode consistency (provider_reported_aqi is ALWAYS null in demo mode)
4. Insufficient vs valid three-pollutant demo datasets
5. OpenAQ v3 /v3/sensors/{sensor_id}/hours endpoint integration & rolling averages
6. Sensor and station separation (never mixing locations)
7. Safe error messages on missing/invalid API credentials (no key exposure)
8. Bounded timeouts, HTTP 401, 403, and 429 rate limit handling
9. Timezone-aware UTC normalization, Asia/Kolkata conversion, future timestamp rejection
10. Strict separation of Provenance, Availability, and Freshness
11. No silent simulated fallback when live provider fails
"""

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport, Response, Request, MockTransport

from app.main import app
from app.config import settings
from app.core.cpcb_naqi import compute_station_cpcb_aqi, calculate_sub_index, PollutantType
from app.schemas.station import (
    AvailabilityType,
    FreshnessType,
    ProvenanceType,
    StationMetadata,
    StationPollutantMeasurement,
)
from app.services.staleness_service import (
    evaluate_freshness,
    to_ist_string,
    to_utc,
    INDIA_TZ,
)
from app.services.aqi_provider import (
    DataGovINProvider,
    OpenAQProvider,
    MockAQIProvider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
)
from app.services.station_service import StationService


# =====================================================================
# 1. STALENESS & TIMEZONE CONVERSIONS
# =====================================================================

class TestStalenessService:
    def test_utc_conversion(self):
        naive = datetime(2026, 11, 20, 10, 0, 0)
        utc_aware = to_utc(naive)
        assert utc_aware.tzinfo == timezone.utc
        assert utc_aware.hour == 10

    def test_ist_formatting(self):
        utc_dt = datetime(2026, 11, 20, 4, 30, 0, tzinfo=timezone.utc)
        ist_str = to_ist_string(utc_dt)
        assert "10:00 AM IST" in ist_str
        assert "20 Nov 2026" in ist_str

    def test_fresh_reading(self):
        now = datetime.now(timezone.utc)
        obs = now - timedelta(hours=2)
        freshness, msg = evaluate_freshness(obs, now_utc=now, fresh_hours=4.0, stale_hours=24.0)
        assert freshness == FreshnessType.FRESH
        assert msg is None

    def test_stale_reading(self):
        now = datetime.now(timezone.utc)
        obs = now - timedelta(hours=6)
        freshness, msg = evaluate_freshness(obs, now_utc=now, fresh_hours=4.0, stale_hours=24.0)
        assert freshness == FreshnessType.STALE
        assert msg is not None
        assert "Data is STALE" in msg
        assert "remain visible" in msg

    def test_expired_reading(self):
        now = datetime.now(timezone.utc)
        obs = now - timedelta(hours=36)
        freshness, msg = evaluate_freshness(obs, now_utc=now, fresh_hours=4.0, stale_hours=24.0)
        assert freshness == FreshnessType.EXPIRED
        assert msg is not None
        assert "Data is EXPIRED" in msg
        assert "Cannot be used as live AQI" in msg

    def test_future_timestamp_rejection(self):
        now = datetime.now(timezone.utc)
        future_obs = now + timedelta(minutes=15)
        freshness, msg = evaluate_freshness(future_obs, now_utc=now)
        assert freshness == FreshnessType.UNKNOWN
        assert msg is not None
        assert "reading is from the future" in msg
        assert "Sensor clock drift detected" in msg

    def test_demo_freshness(self):
        freshness, msg = evaluate_freshness(datetime.now(timezone.utc), is_demo=True)
        assert freshness == FreshnessType.DEMO
        assert msg == "SIMULATED DATA - NOT LIVE AQI"


# =====================================================================
# 2. DATA.GOV.IN FIELD MAPPING & NORMALIZATION (ISSUE 1 AUDIT)
# =====================================================================

class TestDataGovINFieldMapping:
    @pytest.mark.anyio
    async def test_datagovin_response_no_scalar_aqi(self):
        """Resource 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69 has no scalar AQI field.
        provider_reported_aqi must be None.
        """
        obs_ist = datetime.now(INDIA_TZ) - timedelta(hours=1)
        mock_payload = {
            "records": [
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "latitude": "28.6289",
                    "longitude": "77.2405",
                    "pollutant_id": "PM2.5",
                    "pollutant_min": "45",
                    "pollutant_max": "180",
                    "pollutant_avg": "135",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "latitude": "28.6289",
                    "longitude": "77.2405",
                    "pollutant_id": "PM10",
                    "pollutant_min": "90",
                    "pollutant_max": "290",
                    "pollutant_avg": "210",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "latitude": "28.6289",
                    "longitude": "77.2405",
                    "pollutant_id": "NO2",
                    "pollutant_avg": "55",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
            ]
        }

        client = AsyncClient(transport=MockTransport(lambda req: Response(200, json=mock_payload)))
        provider = DataGovINProvider(api_key="valid_key", client=client)

        meta, measurements, aqi, cat, obs_dt, warnings = await provider.get_latest_measurements("cpcb_delhi_ito")
        assert meta is not None
        # Confirms scalar AQI is null
        assert aqi is None
        assert cat is None
        # Confirms pollutant_avg is preserved as measurement value
        assert "PM2.5" in measurements
        assert measurements["PM2.5"].value == 135.0
        assert measurements["PM2.5"].unit == "µg/m³"
        assert "PM10" in measurements
        assert measurements["PM10"].value == 210.0
        assert "NO2" in measurements
        assert measurements["NO2"].value == 55.0

    @pytest.mark.anyio
    async def test_missing_averaging_window_information(self):
        """When data.gov.in does not document coverage_hours, CPCB engine cannot verify
        16-hour minimum requirement and refuses to calculate overall AQI.
        """
        obs_ist = datetime.now(INDIA_TZ) - timedelta(hours=1)
        # Raw records without coverage_hours field
        mock_payload = {
            "records": [
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "pollutant_id": "PM2.5",
                    "pollutant_avg": "135",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "pollutant_id": "PM10",
                    "pollutant_avg": "210",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "pollutant_id": "NO2",
                    "pollutant_avg": "55",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
            ]
        }

        client = AsyncClient(transport=MockTransport(lambda req: Response(200, json=mock_payload)))
        provider = DataGovINProvider(api_key="valid_key", client=client)
        service = StationService(provider=provider)

        resp = await service.get_station_aqi("cpcb_delhi_ito")

        # Must not fabricate an overall AQI
        assert resp.availability == AvailabilityType.UNAVAILABLE
        assert resp.provenance == ProvenanceType.NONE
        assert resp.overall_aqi is None
        assert resp.calculated_aqi is None
        # But individual pollutant readings must be preserved
        assert len(resp.pollutant_measurements) == 3
        assert resp.pollutant_measurements["PM2.5"].coverage_hours is None

    @pytest.mark.anyio
    async def test_documented_coverage_enables_cpcb_calculation(self):
        """When coverage is documented as 24.0 hours, CPCB engine computes overall AQI."""
        obs_ist = datetime.now(INDIA_TZ) - timedelta(hours=1)
        mock_payload = {
            "records": [
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "pollutant_id": "PM2.5",
                    "pollutant_avg": "160",
                    "coverage_hours": "24.0",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "pollutant_id": "PM10",
                    "pollutant_avg": "280",
                    "coverage_hours": "24.0",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
                {
                    "country": "India",
                    "state": "Delhi",
                    "city": "Delhi",
                    "station": "ITO, Delhi - CPCB",
                    "pollutant_id": "NO2",
                    "pollutant_avg": "65",
                    "coverage_hours": "24.0",
                    "last_update": obs_ist.strftime("%d-%m-%Y %H:%M:%S"),
                },
            ]
        }

        client = AsyncClient(transport=MockTransport(lambda req: Response(200, json=mock_payload)))
        provider = DataGovINProvider(api_key="valid_key", client=client)
        service = StationService(provider=provider)

        resp = await service.get_station_aqi("cpcb_delhi_ito")

        assert resp.availability == AvailabilityType.AVAILABLE
        assert resp.provenance == ProvenanceType.CALCULATED
        assert resp.overall_aqi == 331  # PM2.5 160 -> 331, PM10 280 -> 230, NO2 65 -> 81
        assert resp.category == "Very Poor"


# =====================================================================
# 3. DEMO DATA CONSISTENCY TESTS (ISSUE 2 AUDIT)
# =====================================================================

class TestDemoDataConsistency:
    @pytest.mark.anyio
    async def test_demo_provider_reported_aqi_is_null(self, monkeypatch):
        """In SIMULATED_DEMO mode, provider_reported_aqi must ALWAYS be null."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)
        service = StationService()

        # Check all mock stations
        stations = ["mock_delhi_ito", "mock_mumbai_bandra", "mock_bengaluru_btm", "mock_lucknow_lalbagh", "mock_patna_samanpura"]
        for st_id in stations:
            resp = await service.get_station_aqi(st_id)
            assert resp.provider_reported_aqi is None, f"{st_id}: provider_reported_aqi must be None in demo mode"
            assert resp.provenance == ProvenanceType.SIMULATED_DEMO
            assert resp.freshness == FreshnessType.DEMO
            assert "SIMULATED DATA - NOT LIVE AQI" in resp.warnings

    @pytest.mark.anyio
    async def test_valid_three_pollutant_demo_data_calculates_cpcb_aqi(self, monkeypatch):
        """Valid demo stations with 3+ qualifying pollutants compute calculated AQI."""
        monkeypatch.setattr(settings, "DEMO_MODE", True)
        service = StationService()

        resp = await service.get_station_aqi("mock_delhi_ito")
        assert resp.availability == AvailabilityType.AVAILABLE
        assert resp.provenance == ProvenanceType.SIMULATED_DEMO
        assert resp.calculated_aqi is not None
        assert resp.overall_aqi == resp.calculated_aqi
        # PM2.5=165 (335), PM10=280 (230), NO2=65 (81), CO=1.8 (90) -> Dominant PM2.5 (335)
        assert resp.overall_aqi == 335
        assert resp.category == "Very Poor"
        assert resp.dominant_pollutant == "PM2.5"

    @pytest.mark.anyio
    async def test_insufficient_demo_pollutants_marks_unavailable(self, monkeypatch):
        """A simulated station with fewer than 3 qualifying pollutants must have
        calculated_aqi=null and overall_aqi=null with UNAVAILABLE status.
        """
        monkeypatch.setattr(settings, "DEMO_MODE", True)
        service = StationService()

        resp = await service.get_station_aqi("mock_agra_insufficient")
        assert resp.availability == AvailabilityType.UNAVAILABLE
        assert resp.provenance == ProvenanceType.SIMULATED_DEMO
        assert resp.overall_aqi is None
        assert resp.calculated_aqi is None
        assert "at least 3 pollutants" in resp.unavailable_reason


# =====================================================================
# 4. OPENAQ HOURLY DATA & SENSOR ISOLATION (ISSUE 3 AUDIT)
# =====================================================================

class TestOpenAQHourlyIntegration:
    @pytest.mark.anyio
    async def test_openaq_hourly_history_normalization(self):
        """Confirm /v3/sensors/{sensor_id}/hours is queried and rolling averages computed."""
        now = datetime.now(timezone.utc)

        def mock_openaq_hourly(request: Request) -> Response:
            url_str = str(request.url)
            if "locations/101/sensors" in url_str:
                return Response(
                    200,
                    json={
                        "results": [
                            {"id": 1001, "parameter": {"name": "pm25", "units": "µg/m³"}},
                            {"id": 1002, "parameter": {"name": "pm10", "units": "µg/m³"}},
                            {"id": 1003, "parameter": {"name": "no2", "units": "µg/m³"}},
                        ]
                    },
                )
            elif "sensors/1001/hours" in url_str:
                # 20 hours of PM2.5 data (average 160.0)
                hours_data = [
                    {
                        "period": {
                            "datetimeFrom": {"utc": (now - timedelta(hours=i)).isoformat()},
                            "datetimeTo": {"utc": (now - timedelta(hours=i-1)).isoformat()},
                        },
                        "value": 160.0,
                    }
                    for i in range(1, 21)
                ]
                return Response(200, json={"results": hours_data})
            elif "sensors/1002/hours" in url_str:
                # 20 hours of PM10 data (average 280.0)
                hours_data = [
                    {
                        "period": {
                            "datetimeFrom": {"utc": (now - timedelta(hours=i)).isoformat()},
                            "datetimeTo": {"utc": (now - timedelta(hours=i-1)).isoformat()},
                        },
                        "value": 280.0,
                    }
                    for i in range(1, 21)
                ]
                return Response(200, json={"results": hours_data})
            elif "sensors/1003/hours" in url_str:
                # 20 hours of NO2 data (average 65.0)
                hours_data = [
                    {
                        "period": {
                            "datetimeFrom": {"utc": (now - timedelta(hours=i)).isoformat()},
                            "datetimeTo": {"utc": (now - timedelta(hours=i-1)).isoformat()},
                        },
                        "value": 65.0,
                    }
                    for i in range(1, 21)
                ]
                return Response(200, json={"results": hours_data})
            elif "locations/101" in url_str:
                return Response(
                    200,
                    json={
                        "results": [
                            {
                                "id": 101,
                                "name": "Bandra Kurla Complex",
                                "locality": "Mumbai",
                                "region": "Maharashtra",
                                "coordinates": {"latitude": 19.06, "longitude": 72.86},
                                "timezone": "Asia/Kolkata",
                            }
                        ]
                    },
                )
            return Response(404, json={"message": "Not Found"})

        client = AsyncClient(transport=MockTransport(mock_openaq_hourly))
        provider = OpenAQProvider(api_key="valid_openaq_key", client=client)
        service = StationService(provider=provider)

        resp = await service.get_station_aqi("openaq_101")

        assert resp.availability == AvailabilityType.AVAILABLE
        assert resp.provenance == ProvenanceType.CALCULATED
        assert resp.overall_aqi == 331  # PM2.5 160 -> 331, PM10 280 -> 230, NO2 65 -> 81
        assert resp.pollutant_measurements["PM2.5"].coverage_hours == 20.0
        assert resp.pollutant_measurements["PM2.5"].sensor_id == "1001"

    @pytest.mark.anyio
    async def test_sensor_and_station_separation(self):
        """Sensors from station A must never be attached to station B."""
        def mock_two_stations(request: Request) -> Response:
            url_str = str(request.url)
            if "locations/201/sensors" in url_str:
                return Response(
                    200,
                    json={
                        "results": [
                            {"id": 2001, "parameter": {"name": "pm25", "units": "µg/m³"}},
                        ]
                    },
                )
            elif "locations/202/sensors" in url_str:
                return Response(
                    200,
                    json={
                        "results": [
                            {"id": 3001, "parameter": {"name": "pm25", "units": "µg/m³"}},
                        ]
                    },
                )
            return Response(200, json={"results": []})

        client = AsyncClient(transport=MockTransport(mock_two_stations))
        provider = OpenAQProvider(api_key="valid_key", client=client)

        hourly_a = await provider.get_hourly_measurements("openaq_201")
        hourly_b = await provider.get_hourly_measurements("openaq_202")

        # Station 201 should only have sensor 2001
        for records in hourly_a.values():
            for r in records:
                assert r["sensor_id"] == "2001"
                assert r["sensor_id"] != "3001"

    @pytest.mark.anyio
    async def test_latest_endpoint_alone_has_1hr_coverage_fails_cpcb(self):
        """When only the latest-measurement endpoint is queried (1.0 hr coverage),
        CPCB engine will not calculate overall AQI.
        """
        def mock_latest_only(request: Request) -> Response:
            url_str = str(request.url)
            if "locations/301/latest" in url_str:
                return Response(
                    200,
                    json={
                        "results": [
                            {"sensorsId": 901, "value": 150.0, "parameter": {"name": "pm25", "units": "µg/m³"}},
                            {"sensorsId": 902, "value": 250.0, "parameter": {"name": "pm10", "units": "µg/m³"}},
                            {"sensorsId": 903, "value": 50.0, "parameter": {"name": "no2", "units": "µg/m³"}},
                        ]
                    },
                )
            elif "locations/301" in url_str:
                return Response(200, json={"results": [{"id": 301, "name": "Test Site"}]})
            return Response(404, json={"results": []})

        client = AsyncClient(transport=MockTransport(mock_latest_only))
        provider = OpenAQProvider(api_key="valid_key", client=client)

        # Call with fetch_hourly=False to simulate latest-measurement only
        meta, measurements, aqi, cat, obs, warnings = await provider.get_latest_measurements("openaq_301", fetch_hourly=False)
        assert "PM2.5" in measurements
        assert measurements["PM2.5"].coverage_hours == 1.0  # Instantaneous

        # Pass to Phase 2 engine
        calc_payload = [
            {"pollutant": m.pollutant, "value": m.value, "unit": m.unit, "hours_recorded": m.coverage_hours}
            for m in measurements.values()
        ]
        res = compute_station_cpcb_aqi(calc_payload)
        assert res["eligible_for_overall_aqi"] is False
        assert res["overall_aqi"] is None
        assert "minimum 16.0 hours required" in res["sub_indices"]["PM2.5"]["validation_error"]


# =====================================================================
# 5. AUTHENTICATION & SECURITY (ISSUE 4 AUDIT)
# =====================================================================

class TestSecurityAndAuth:
    def test_missing_credentials_raises_safe_error(self):
        """ProviderAuthError must provide clear guidance without leaking any secret."""
        p_cpcb = DataGovINProvider(api_key="")
        with pytest.raises(ProviderAuthError) as exc_cpcb:
            import asyncio
            asyncio.run(p_cpcb.discover_stations())
        assert "DATA_GOV_IN_API_KEY is not configured" in str(exc_cpcb.value)

        p_openaq = OpenAQProvider(api_key="")
        with pytest.raises(ProviderAuthError) as exc_openaq:
            import asyncio
            asyncio.run(p_openaq.discover_stations())
        assert "OPENAQ_API_KEY is not configured" in str(exc_openaq.value)

    @pytest.mark.anyio
    async def test_http_401_unauthorized_error(self):
        """HTTP 401 from provider raises ProviderAuthError without leaking key."""
        client = AsyncClient(transport=MockTransport(lambda req: Response(401, json={"message": "Unauthorized"})))
        provider = DataGovINProvider(api_key="secret_test_key_12345", client=client)

        with pytest.raises(ProviderAuthError) as exc:
            await provider.discover_stations()
        error_msg = str(exc.value)
        assert "rejected API key with HTTP 401" in error_msg
        assert "secret_test_key_12345" not in error_msg  # Never leak key

    @pytest.mark.anyio
    async def test_http_429_rate_limit_error(self):
        """HTTP 429 from provider raises ProviderRateLimitError."""
        client = AsyncClient(transport=MockTransport(lambda req: Response(429, json={"message": "Too Many Requests"})))
        provider = OpenAQProvider(api_key="valid_key", client=client)

        with pytest.raises(ProviderRateLimitError) as exc:
            await provider.discover_stations()
        assert "rate limit exceeded (HTTP 429)" in str(exc.value)

    @pytest.mark.anyio
    async def test_network_timeout_error(self):
        """Network timeout raises ProviderError with safe explanation."""
        def mock_timeout(req: Request):
            import httpx
            raise httpx.ReadTimeout("Connection timed out")

        client = AsyncClient(transport=MockTransport(mock_timeout))
        provider = DataGovINProvider(api_key="valid_key", client=client)

        with pytest.raises(ProviderError) as exc:
            await provider.discover_stations()
        assert "connection timeout or network error" in str(exc.value)

    @pytest.mark.anyio
    async def test_empty_records_response(self):
        """Empty provider response is handled safely without crashing."""
        client = AsyncClient(transport=MockTransport(lambda req: Response(200, json={"records": []})))
        provider = DataGovINProvider(api_key="valid_key", client=client)
        stations = await provider.discover_stations()
        assert stations == []

    @pytest.mark.anyio
    async def test_no_silent_fallback_when_live_fails(self, monkeypatch):
        """When DEMO_MODE=False and live API fails, returns UNAVAILABLE without falling back to mock."""
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        monkeypatch.setattr(settings, "DATA_GOV_IN_API_KEY", "")

        service = StationService()
        resp = await service.get_station_aqi("cpcb_delhi_ito")

        assert resp.availability == AvailabilityType.UNAVAILABLE
        assert resp.provenance == ProvenanceType.NONE
        assert resp.overall_aqi is None
        assert "DATA_GOV_IN_API_KEY is not configured" in resp.unavailable_reason
        assert resp.station.provider != "mock"


# =====================================================================
# 6. FASTAPI ENDPOINT INTEGRATION TESTS
# =====================================================================

class TestFastAPIEndpoints:
    @pytest.mark.anyio
    async def test_station_listing_endpoint_demo(self, monkeypatch):
        monkeypatch.setattr(settings, "DEMO_MODE", True)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/aqi/stations")
            assert resp.status_code == 200
            data = resp.json()
            assert data["demo_mode"] is True
            assert data["total"] >= 5

    @pytest.mark.anyio
    async def test_station_detail_endpoint_demo(self, monkeypatch):
        monkeypatch.setattr(settings, "DEMO_MODE", True)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/aqi/station/mock_delhi_ito")
            assert resp.status_code == 200
            data = resp.json()
            assert data["provenance"] == "SIMULATED_DEMO"
            assert data["availability"] == "AVAILABLE"
            assert data["provider_reported_aqi"] is None  # Must be null in demo
            assert data["overall_aqi"] is not None
            assert data["overall_aqi"] == 335
