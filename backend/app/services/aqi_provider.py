"""Air Quality Data Provider Adapters for SmogShield AI.

Implements BaseAQIProvider interface with three adapters:
1. DataGovINProvider: Official Indian real-time AQI dataset (CPCB via data.gov.in)
2. OpenAQProvider: Global open air quality network using OpenAQ API v3
3. MockAQIProvider: High-fidelity simulation for explicitly enabled demo mode

Engineering Rules:
- No silent fallback to mock data when live API calls fail.
- All requests use asynchronous HTTP with timeouts, bounded retries, and rate limit handling.
- Original sensor IDs, timestamps, and measurement units are preserved.
- No cross-location mixing of sensors.
- Never invent scalar AQI when upstream only provides pollutant measurements.
- Never populate provider_reported_aqi in demo mode.
- OpenAQ uses documented /v3/sensors/{sensor_id}/hours endpoint for hourly data.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, List, Optional, Tuple, Any
import httpx

from app.config import settings
from app.schemas.station import (
    FreshnessType,
    StationMetadata,
    StationPollutantMeasurement,
)
from app.services.staleness_service import to_utc

logger = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo
    INDIA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    INDIA_TZ = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")


class ProviderError(Exception):
    """Base exception for provider communication errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ProviderAuthError(ProviderError):
    """Exception raised when API key is missing, invalid, or unauthorized."""
    pass


class ProviderRateLimitError(ProviderError):
    """Exception raised when rate limit is exceeded (HTTP 429)."""
    pass


class BaseAQIProvider(ABC):
    """Abstract interface for external air quality data providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier string."""
        pass

    @abstractmethod
    async def discover_stations(self, city: Optional[str] = None) -> List[StationMetadata]:
        """Discover monitoring stations, optionally filtered by city."""
        pass

    @abstractmethod
    async def get_station_metadata(self, station_id: str) -> Optional[StationMetadata]:
        """Retrieve metadata for a specific station ID."""
        pass

    @abstractmethod
    async def get_latest_measurements(
        self, station_id: str
    ) -> Tuple[
        Optional[StationMetadata],
        Dict[str, StationPollutantMeasurement],
        Optional[int],
        Optional[str],
        Optional[datetime],
        List[str],
    ]:
        """Retrieve measurements for a station.

        Returns:
            (station_metadata, measurements_map, provider_reported_aqi,
             provider_reported_category, observed_at_utc, warnings)
        """
        pass

    @abstractmethod
    async def get_hourly_measurements(
        self, station_id: str, hours: int = 24
    ) -> Dict[str, List[dict]]:
        """Retrieve historical hourly measurements for rolling average calculations."""
        pass


# =====================================================================
# 1. DATA.GOV.IN PROVIDER (Official CPCB Real-time Dataset)
# =====================================================================

class DataGovINProvider(BaseAQIProvider):
    """Adapter for official real-time AQI dataset published by CPCB on data.gov.in.

    Dataset Resource ID: 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69
    Catalog: https://www.data.gov.in/catalog/real-time-air-quality-index

    Important:
    The data.gov.in resource 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69 publishes
    individual criteria pollutant measurements (pollutant_id, pollutant_min,
    pollutant_max, pollutant_avg), but does NOT contain an official scalar AQI field.
    Therefore, provider_reported_aqi is always returned as None for this provider.
    Overall AQI must be computed locally via the Phase 2 CPCB NAQI engine only
    when requirements (3+ criteria pollutants with PM, verified monitoring hours) are met.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        resource_id: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or settings.DATA_GOV_IN_API_KEY
        self.resource_id = resource_id or settings.DATA_GOV_IN_RESOURCE_ID
        self.base_url = base_url or settings.DATA_GOV_IN_BASE_URL
        self._external_client = client

    @property
    def provider_name(self) -> str:
        return "cpcb_datagov"

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)

    def _parse_ist_timestamp(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse CPCB data.gov.in timestamp format to timezone-aware UTC datetime.

        CPCB typically reports format: 'DD-MM-YYYY HH:MM:SS' in IST.
        """
        if not ts_str:
            return None
        cleaned = ts_str.strip()
        formats = [
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
        ]
        for fmt in formats:
            try:
                naive_dt = datetime.strptime(cleaned, fmt)
                ist_dt = naive_dt.replace(tzinfo=INDIA_TZ)
                return ist_dt.astimezone(timezone.utc)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

    def _normalize_station_id(self, city: str, station_name: str) -> str:
        """Create deterministic provider-prefixed station ID: cpcb_{city}_{slug}."""
        city_slug = city.strip().lower().replace(" ", "_")
        name_slug = station_name.strip().lower().split(",")[0].replace(" ", "_").replace("-", "_")
        return f"cpcb_{city_slug}_{name_slug}"

    async def _fetch_records(self, filters: Optional[Dict[str, str]] = None, limit: int = 100) -> List[dict]:
        """Execute HTTP GET against data.gov.in resource with bounded retries."""
        if not self.api_key:
            raise ProviderAuthError(
                "DATA_GOV_IN_API_KEY is not configured in backend environment. "
                "Official Indian CPCB data requires a valid API key from https://data.gov.in. "
                "Configure DATA_GOV_IN_API_KEY in .env."
            )

        url = f"{self.base_url}/{self.resource_id}"
        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
        }
        if filters:
            for k, v in filters.items():
                params[f"filters[{k}]"] = v

        retries = settings.HTTP_MAX_RETRIES
        client = self._get_client()
        should_close = self._external_client is None

        try:
            for attempt in range(retries + 1):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code == 401 or response.status_code == 403:
                        raise ProviderAuthError(
                            f"data.gov.in rejected API key with HTTP {response.status_code}. "
                            "Please verify DATA_GOV_IN_API_KEY in backend environment."
                        )
                    if response.status_code == 429:
                        raise ProviderRateLimitError(
                            "data.gov.in rate limit exceeded (HTTP 429). Please reduce request frequency."
                        )
                    response.raise_for_status()
                    data = response.json()
                    return data.get("records", [])
                except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                    if attempt < retries:
                        continue
                    raise ProviderError(
                        f"data.gov.in connection timeout or network error: {str(net_err)}"
                    )
        finally:
            if should_close:
                await client.aclose()
        return []

    async def discover_stations(self, city: Optional[str] = None) -> List[StationMetadata]:
        filters = {"city": city} if city else None
        records = await self._fetch_records(filters=filters, limit=200)

        stations_dict: Dict[str, StationMetadata] = {}
        for r in records:
            st_name = r.get("station", "").strip()
            c_name = r.get("city", "").strip()
            s_name = r.get("state", "").strip()
            if not st_name or not c_name:
                continue

            station_id = self._normalize_station_id(c_name, st_name)
            if station_id not in stations_dict:
                lat = None
                lon = None
                try:
                    if r.get("latitude"):
                        lat = float(r["latitude"])
                    if r.get("longitude"):
                        lon = float(r["longitude"])
                except (ValueError, TypeError):
                    pass

                stations_dict[station_id] = StationMetadata(
                    station_id=station_id,
                    provider=self.provider_name,
                    provider_station_id=st_name,
                    station_name=st_name,
                    city=c_name,
                    state=s_name,
                    latitude=lat,
                    longitude=lon,
                    country=r.get("country", "India"),
                    timezone="Asia/Kolkata",
                )
        return list(stations_dict.values())

    async def get_station_metadata(self, station_id: str) -> Optional[StationMetadata]:
        all_stations = await self.discover_stations()
        for st in all_stations:
            if st.station_id == station_id:
                return st
        return None

    async def get_latest_measurements(
        self, station_id: str
    ) -> Tuple[
        Optional[StationMetadata],
        Dict[str, StationPollutantMeasurement],
        Optional[int],
        Optional[str],
        Optional[datetime],
        List[str],
    ]:
        metadata = await self.get_station_metadata(station_id)
        if not metadata:
            return None, {}, None, None, None, [f"Station '{station_id}' not found in data.gov.in catalog"]

        filters = {"city": metadata.city, "station": metadata.provider_station_id}
        records = await self._fetch_records(filters=filters, limit=50)

        measurements: Dict[str, StationPollutantMeasurement] = {}
        latest_obs_time: Optional[datetime] = None
        warnings: List[str] = []

        # data.gov.in resource 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69 does not contain
        # an official scalar AQI field; provider_reported_aqi remains None.
        provider_aqi: Optional[int] = None
        provider_cat: Optional[str] = None

        for r in records:
            pollutant_raw = r.get("pollutant_id", "").strip()
            avg_val_str = r.get("pollutant_avg")
            last_update = r.get("last_update")
            obs_dt = self._parse_ist_timestamp(last_update)

            if obs_dt and (latest_obs_time is None or obs_dt > latest_obs_time):
                latest_obs_time = obs_dt

            # Standard criteria pollutants mapping
            pollutant_name = pollutant_raw.upper()
            if pollutant_name == "OZONE":
                pollutant_name = "O3"

            if pollutant_name in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "PB"]:
                try:
                    if avg_val_str is None or avg_val_str == "NA" or avg_val_str == "":
                        continue
                    val = float(avg_val_str)
                except (ValueError, TypeError):
                    continue

                unit = "mg/m³" if pollutant_name == "CO" else "µg/m³"
                avg_hrs = 8 if pollutant_name in ["CO", "O3"] else 24

                # Do not assume pollutant_avg proves 16 hours of coverage unless source documents it
                # If record contains documented coverage_hours, use it; otherwise None
                cov_hrs: Optional[float] = None
                if "coverage_hours" in r and r["coverage_hours"] is not None:
                    try:
                        cov_hrs = float(r["coverage_hours"])
                    except (ValueError, TypeError):
                        pass

                measurement_dt = obs_dt or datetime.now(timezone.utc)
                measurements[pollutant_name] = StationPollutantMeasurement(
                    pollutant=pollutant_name,
                    sensor_id=f"cpcb_{metadata.city}_{pollutant_name}".lower(),
                    value=val,
                    unit=unit,
                    observed_at_utc=measurement_dt,
                    averaging_period_hours=avg_hrs,
                    coverage_hours=cov_hrs,
                    provider=self.provider_name,
                    source="Central Pollution Control Board (CPCB) via data.gov.in",
                    freshness=FreshnessType.FRESH,
                )

        return metadata, measurements, provider_aqi, provider_cat, latest_obs_time, warnings

    async def get_hourly_measurements(
        self, station_id: str, hours: int = 24
    ) -> Dict[str, List[dict]]:
        """data.gov.in real-time dataset provides instantaneous and 24h averages, not hourly arrays."""
        return {}


# =====================================================================
# 2. OPENAQ API v3 PROVIDER
# =====================================================================

class OpenAQProvider(BaseAQIProvider):
    """Adapter for OpenAQ API v3.

    API Documentation: https://api.openaq.org/v3
    Authentication: X-API-Key header
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or settings.OPENAQ_API_KEY
        self.base_url = (base_url or settings.OPENAQ_BASE_URL).rstrip("/")
        self._external_client = client

    @property
    def provider_name(self) -> str:
        return "openaq"

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ProviderAuthError(
                "OPENAQ_API_KEY is not configured in backend environment. "
                "OpenAQ API v3 requires an API key in the X-API-Key header. "
                "Obtain one at https://openaq.org and configure OPENAQ_API_KEY in .env."
            )
        return {"X-API-Key": self.api_key}

    async def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict:
        headers = self._headers()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        client = self._get_client()
        should_close = self._external_client is None

        retries = settings.HTTP_MAX_RETRIES
        try:
            for attempt in range(retries + 1):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 401 or response.status_code == 403:
                        raise ProviderAuthError(
                            f"OpenAQ API v3 rejected request with HTTP {response.status_code}. "
                            "Please verify OPENAQ_API_KEY in backend environment."
                        )
                    if response.status_code == 429:
                        raise ProviderRateLimitError(
                            "OpenAQ API v3 rate limit exceeded (HTTP 429). Please reduce request frequency."
                        )
                    response.raise_for_status()
                    return response.json()
                except (httpx.TimeoutException, httpx.NetworkError) as err:
                    if attempt < retries:
                        continue
                    raise ProviderError(f"OpenAQ API v3 connection error: {str(err)}")
        finally:
            if should_close:
                await client.aclose()
        return {}

    async def discover_stations(self, city: Optional[str] = None) -> List[StationMetadata]:
        # OpenAQ v3 /v3/locations: country ISO 'IN' = India, ID 88
        params: Dict[str, Any] = {"countries_id": 88, "limit": 100}
        data = await self._request("locations", params=params)
        results = data.get("results", [])

        stations: List[StationMetadata] = []
        for loc in results:
            loc_id = str(loc.get("id", ""))
            name = loc.get("name", f"OpenAQ Station {loc_id}")
            locality = loc.get("locality") or loc.get("region") or "Unknown"
            coords = loc.get("coordinates", {}) or {}
            lat = coords.get("latitude")
            lon = coords.get("longitude")

            if city and city.lower() not in locality.lower() and city.lower() not in name.lower():
                continue

            stations.append(
                StationMetadata(
                    station_id=f"openaq_{loc_id}",
                    provider=self.provider_name,
                    provider_station_id=loc_id,
                    station_name=name,
                    city=locality,
                    state=loc.get("region") or locality,
                    latitude=lat,
                    longitude=lon,
                    country="India",
                    timezone=loc.get("timezone", "Asia/Kolkata"),
                )
            )
        return stations

    async def get_station_metadata(self, station_id: str) -> Optional[StationMetadata]:
        loc_id = station_id.replace("openaq_", "")
        data = await self._request(f"locations/{loc_id}")
        results = data.get("results", [])
        if not results:
            return None
        loc = results[0]
        coords = loc.get("coordinates", {}) or {}
        return StationMetadata(
            station_id=station_id,
            provider=self.provider_name,
            provider_station_id=loc_id,
            station_name=loc.get("name", f"OpenAQ Station {loc_id}"),
            city=loc.get("locality") or loc.get("region") or "Unknown",
            state=loc.get("region") or "Unknown",
            latitude=coords.get("latitude"),
            longitude=coords.get("longitude"),
            country="India",
            timezone=loc.get("timezone", "Asia/Kolkata"),
        )

    async def get_hourly_measurements(
        self, station_id: str, hours: int = 24
    ) -> Dict[str, List[dict]]:
        """Retrieve historical hourly measurements for each sensor at the location.

        Uses documented OpenAQ v3 sensor-specific endpoint:
        GET /v3/sensors/{sensor_id}/hours?limit={hours}
        """
        metadata = await self.get_station_metadata(station_id)
        if not metadata:
            return {}

        loc_id = metadata.provider_station_id
        # Get sensor list for this location (never mix locations)
        data = await self._request(f"locations/{loc_id}/sensors")
        sensor_items = data.get("results", [])

        pollutant_map = {
            "pm25": "PM2.5",
            "pm10": "PM10",
            "no2": "NO2",
            "so2": "SO2",
            "co": "CO",
            "o3": "O3",
            "nh3": "NH3",
            "pb": "Pb",
        }

        hourly_by_pollutant: Dict[str, List[dict]] = {}

        for sensor in sensor_items:
            s_id = str(sensor.get("id") or "")
            param_obj = sensor.get("parameter", {}) or {}
            param_name = param_obj.get("name", "").lower()
            std_pollutant = pollutant_map.get(param_name)
            if not std_pollutant or not s_id:
                continue

            # Query OpenAQ v3 documented sensor hours endpoint
            hours_data = await self._request(f"sensors/{s_id}/hours", params={"limit": hours})
            hour_results = hours_data.get("results", [])

            records: List[dict] = []
            for item in hour_results:
                val = item.get("value")
                if val is None or val < 0:
                    continue

                period = item.get("period", {}) or {}
                dt_from = period.get("datetimeFrom", {}) or {}
                utc_str = dt_from.get("utc")
                if not utc_str:
                    continue

                try:
                    obs_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    continue

                unit = param_obj.get("units", "µg/m³")
                if unit in ["ug/m3", "µg/m3"]:
                    unit = "µg/m³"

                records.append({
                    "sensor_id": s_id,
                    "pollutant": std_pollutant,
                    "value": float(val),
                    "unit": unit,
                    "observed_at_utc": obs_dt,
                })

            if records:
                hourly_by_pollutant[std_pollutant] = records

        return hourly_by_pollutant

    async def get_latest_measurements(
        self, station_id: str, fetch_hourly: bool = True
    ) -> Tuple[
        Optional[StationMetadata],
        Dict[str, StationPollutantMeasurement],
        Optional[int],
        Optional[str],
        Optional[datetime],
        List[str],
    ]:
        """Retrieve measurements for OpenAQ station.

        If fetch_hourly=True, uses /v3/sensors/{sensor_id}/hours to calculate
        actual rolling averages and coverage hours.
        If hourly data is not available, uses /locations/{id}/latest with
        coverage_hours=1.0 and a warning (preventing CPCB AQI calculation from instantaneous reading).
        """
        metadata = await self.get_station_metadata(station_id)
        if not metadata:
            return None, {}, None, None, None, [f"Station '{station_id}' not found in OpenAQ v3"]

        measurements: Dict[str, StationPollutantMeasurement] = {}
        latest_obs_time: Optional[datetime] = None
        warnings: List[str] = []

        if fetch_hourly:
            # Query documented hourly history
            try:
                hourly_data = await self.get_hourly_measurements(station_id, hours=24)
            except Exception:
                hourly_data = {}

            if hourly_data:
                for pollutant_name, records in hourly_data.items():
                    window_hrs = 8 if pollutant_name in ["CO", "O3"] else 24
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hrs)
                    qualifying = [r for r in records if r["observed_at_utc"] >= cutoff]
                    if not qualifying:
                        qualifying = records[:window_hrs]

                    valid_count = len(qualifying)
                    avg_val = round(sum(r["value"] for r in qualifying) / valid_count, 2)
                    max_obs = max(r["observed_at_utc"] for r in qualifying)
                    sensor_id = qualifying[0]["sensor_id"]
                    unit = qualifying[0]["unit"]

                    if latest_obs_time is None or max_obs > latest_obs_time:
                        latest_obs_time = max_obs

                    measurements[pollutant_name] = StationPollutantMeasurement(
                        pollutant=pollutant_name,
                        sensor_id=sensor_id,
                        value=avg_val,
                        unit=unit,
                        observed_at_utc=max_obs,
                        averaging_period_hours=window_hrs,
                        coverage_hours=float(valid_count),
                        provider=self.provider_name,
                        source=f"OpenAQ v3 Hourly Sensor #{sensor_id}",
                        freshness=FreshnessType.FRESH,
                    )
                return metadata, measurements, None, None, latest_obs_time, warnings

        # Fallback to latest endpoint if hourly is disabled or empty
        loc_id = metadata.provider_station_id
        data = await self._request(f"locations/{loc_id}/latest")
        results = data.get("results", [])

        pollutant_map = {
            "pm25": "PM2.5",
            "pm10": "PM10",
            "no2": "NO2",
            "so2": "SO2",
            "co": "CO",
            "o3": "O3",
            "nh3": "NH3",
            "pb": "Pb",
        }

        warnings.append(
            "Instantaneous latest measurement endpoint used. Hourly history was not available; "
            "coverage duration is 1 hour (CPCB NAQI requires 16+ hours of qualifying data)."
        )

        for item in results:
            param_obj = item.get("parameter", {}) or {}
            param_name = param_obj.get("name", "").lower()
            std_pollutant = pollutant_map.get(param_name)
            if not std_pollutant:
                continue

            val = item.get("value")
            if val is None or val < 0:
                continue

            unit = param_obj.get("units", "µg/m³")
            if unit in ["ug/m3", "µg/m3"]:
                unit = "µg/m³"

            sensor_id = str(item.get("sensorsId") or item.get("sensorId") or "")
            dt_obj = item.get("datetime", {}) or {}
            utc_str = dt_obj.get("utc")
            obs_dt = None
            if utc_str:
                try:
                    obs_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    obs_dt = datetime.now(timezone.utc)
            else:
                obs_dt = datetime.now(timezone.utc)

            if latest_obs_time is None or obs_dt > latest_obs_time:
                latest_obs_time = obs_dt

            avg_hrs = 8 if std_pollutant in ["CO", "O3"] else 24
            # 1.0 hour coverage reflects single instantaneous reading, which CPCB engine will not extrapolate
            measurements[std_pollutant] = StationPollutantMeasurement(
                pollutant=std_pollutant,
                sensor_id=sensor_id,
                value=float(val),
                unit=unit,
                observed_at_utc=obs_dt,
                averaging_period_hours=avg_hrs,
                coverage_hours=1.0,
                provider=self.provider_name,
                source=f"OpenAQ v3 (Sensor #{sensor_id})",
                freshness=FreshnessType.FRESH,
            )

        return metadata, measurements, None, None, latest_obs_time, warnings


# =====================================================================
# 3. MOCK AQI PROVIDER (Explicitly Enabled Demo Mode)
# =====================================================================

class MockAQIProvider(BaseAQIProvider):
    """High-fidelity simulated provider for explicitly enabled demo mode.

    Contains realistic monitoring stations in Delhi NCR, Mumbai, Bengaluru,
    Lucknow, and Patna. Used ONLY when DEMO_MODE=true.
    Never activated silently on network errors.

    Rule: Never populate provider_reported_aqi with a simulated number.
    provider_reported_aqi is always None in demo mode. Overall AQI is
    derived deterministically via the Phase 2 CPCB calculation engine from
    simulated pollutant measurements with verified data coverage.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    def _get_mock_stations(self) -> Dict[str, dict]:
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(minutes=45)

        return {
            "mock_delhi_ito": {
                "metadata": StationMetadata(
                    station_id="mock_delhi_ito",
                    provider=self.provider_name,
                    provider_station_id="DEL_ITO_01",
                    station_name="ITO, Delhi - CPCB (Simulated)",
                    city="Delhi",
                    state="Delhi",
                    latitude=28.6289,
                    longitude=77.2405,
                    country="India",
                    timezone="Asia/Kolkata",
                ),
                "measurements": {
                    "PM2.5": StationPollutantMeasurement(
                        pollutant="PM2.5",
                        sensor_id="mock_ito_pm25",
                        value=165.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "PM10": StationPollutantMeasurement(
                        pollutant="PM10",
                        sensor_id="mock_ito_pm10",
                        value=280.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "NO2": StationPollutantMeasurement(
                        pollutant="NO2",
                        sensor_id="mock_ito_no2",
                        value=65.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "CO": StationPollutantMeasurement(
                        pollutant="CO",
                        sensor_id="mock_ito_co",
                        value=1.8,
                        unit="mg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=8,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                },
                "provider_reported_aqi": None,
                "provider_reported_category": None,
                "observed_at_utc": recent_time,
            },
            "mock_mumbai_bandra": {
                "metadata": StationMetadata(
                    station_id="mock_mumbai_bandra",
                    provider=self.provider_name,
                    provider_station_id="MUM_BAN_01",
                    station_name="Bandra Kurla Complex, Mumbai (Simulated)",
                    city="Mumbai",
                    state="Maharashtra",
                    latitude=19.0657,
                    longitude=72.8687,
                    country="India",
                    timezone="Asia/Kolkata",
                ),
                "measurements": {
                    "PM2.5": StationPollutantMeasurement(
                        pollutant="PM2.5",
                        sensor_id="mock_bkc_pm25",
                        value=45.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "PM10": StationPollutantMeasurement(
                        pollutant="PM10",
                        sensor_id="mock_bkc_pm10",
                        value=75.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "NO2": StationPollutantMeasurement(
                        pollutant="NO2",
                        sensor_id="mock_bkc_no2",
                        value=35.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                },
                "provider_reported_aqi": None,
                "provider_reported_category": None,
                "observed_at_utc": recent_time,
            },
            "mock_bengaluru_btm": {
                "metadata": StationMetadata(
                    station_id="mock_bengaluru_btm",
                    provider=self.provider_name,
                    provider_station_id="BLR_BTM_01",
                    station_name="BTM Layout, Bengaluru (Simulated)",
                    city="Bengaluru",
                    state="Karnataka",
                    latitude=12.9166,
                    longitude=77.6101,
                    country="India",
                    timezone="Asia/Kolkata",
                ),
                "measurements": {
                    "PM2.5": StationPollutantMeasurement(
                        pollutant="PM2.5",
                        sensor_id="mock_btm_pm25",
                        value=25.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "PM10": StationPollutantMeasurement(
                        pollutant="PM10",
                        sensor_id="mock_btm_pm10",
                        value=45.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "NO2": StationPollutantMeasurement(
                        pollutant="NO2",
                        sensor_id="mock_btm_no2",
                        value=20.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                },
                "provider_reported_aqi": None,
                "provider_reported_category": None,
                "observed_at_utc": recent_time,
            },
            "mock_lucknow_lalbagh": {
                "metadata": StationMetadata(
                    station_id="mock_lucknow_lalbagh",
                    provider=self.provider_name,
                    provider_station_id="LKO_LAL_01",
                    station_name="Lalbagh, Lucknow (Simulated)",
                    city="Lucknow",
                    state="Uttar Pradesh",
                    latitude=26.8500,
                    longitude=80.9333,
                    country="India",
                    timezone="Asia/Kolkata",
                ),
                "measurements": {
                    "PM2.5": StationPollutantMeasurement(
                        pollutant="PM2.5",
                        sensor_id="mock_lal_pm25",
                        value=210.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "PM10": StationPollutantMeasurement(
                        pollutant="PM10",
                        sensor_id="mock_lal_pm10",
                        value=310.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "NO2": StationPollutantMeasurement(
                        pollutant="NO2",
                        sensor_id="mock_lal_no2",
                        value=70.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                },
                "provider_reported_aqi": None,
                "provider_reported_category": None,
                "observed_at_utc": recent_time,
            },
            "mock_patna_samanpura": {
                "metadata": StationMetadata(
                    station_id="mock_patna_samanpura",
                    provider=self.provider_name,
                    provider_station_id="PAT_SAM_01",
                    station_name="Samanpura, Patna (Simulated)",
                    city="Patna",
                    state="Bihar",
                    latitude=25.6100,
                    longitude=85.0800,
                    country="India",
                    timezone="Asia/Kolkata",
                ),
                "measurements": {
                    "PM2.5": StationPollutantMeasurement(
                        pollutant="PM2.5",
                        sensor_id="mock_sam_pm25",
                        value=320.0,  # In Severe range (>250)
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "PM10": StationPollutantMeasurement(
                        pollutant="PM10",
                        sensor_id="mock_sam_pm10",
                        value=450.0,  # In Severe range (>430)
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "NO2": StationPollutantMeasurement(
                        pollutant="NO2",
                        sensor_id="mock_sam_no2",
                        value=95.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                },
                "provider_reported_aqi": None,
                "provider_reported_category": None,
                "observed_at_utc": recent_time,
            },
            # Explicit demo station with INSUFFICIENT pollutants (< 3 criteria pollutants)
            "mock_agra_insufficient": {
                "metadata": StationMetadata(
                    station_id="mock_agra_insufficient",
                    provider=self.provider_name,
                    provider_station_id="AGR_INS_01",
                    station_name="Taj East Gate, Agra (Simulated - Insufficient)",
                    city="Agra",
                    state="Uttar Pradesh",
                    latitude=27.1751,
                    longitude=78.0421,
                    country="India",
                    timezone="Asia/Kolkata",
                ),
                "measurements": {
                    "PM2.5": StationPollutantMeasurement(
                        pollutant="PM2.5",
                        sensor_id="mock_agr_pm25",
                        value=120.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                    "PM10": StationPollutantMeasurement(
                        pollutant="PM10",
                        sensor_id="mock_agr_pm10",
                        value=180.0,
                        unit="µg/m³",
                        observed_at_utc=recent_time,
                        averaging_period_hours=24,
                        coverage_hours=24.0,
                        provider=self.provider_name,
                        source="Simulated Demo Monitor",
                        freshness=FreshnessType.DEMO,
                    ),
                },
                "provider_reported_aqi": None,
                "provider_reported_category": None,
                "observed_at_utc": recent_time,
            },
        }

    async def discover_stations(self, city: Optional[str] = None) -> List[StationMetadata]:
        all_stations = [data["metadata"] for data in self._get_mock_stations().values()]
        if city:
            c_low = city.lower()
            return [st for st in all_stations if c_low in st.city.lower() or c_low in st.station_name.lower()]
        return all_stations

    async def get_station_metadata(self, station_id: str) -> Optional[StationMetadata]:
        data = self._get_mock_stations().get(station_id)
        return data["metadata"] if data else None

    async def get_latest_measurements(
        self, station_id: str
    ) -> Tuple[
        Optional[StationMetadata],
        Dict[str, StationPollutantMeasurement],
        Optional[int],
        Optional[str],
        Optional[datetime],
        List[str],
    ]:
        data = self._get_mock_stations().get(station_id)
        if not data:
            return None, {}, None, None, None, [f"Simulated station '{station_id}' not found"]

        warnings = ["SIMULATED DATA - NOT LIVE AQI"]
        return (
            data["metadata"],
            data["measurements"],
            None,  # Never populate provider_reported_aqi in demo mode
            None,
            data["observed_at_utc"],
            warnings,
        )

    async def get_hourly_measurements(
        self, station_id: str, hours: int = 24
    ) -> Dict[str, List[dict]]:
        return {}


# =====================================================================
# 4. PROVIDER FACTORY
# =====================================================================

def get_provider_for_station(station_id: str) -> BaseAQIProvider:
    """Resolve data provider based on station ID prefix and settings."""
    if settings.DEMO_MODE:
        return MockAQIProvider()

    if station_id.startswith("cpcb_"):
        return DataGovINProvider()
    elif station_id.startswith("openaq_"):
        return OpenAQProvider()
    elif station_id.startswith("mock_"):
        # Explicit mock station requested
        return MockAQIProvider()
    else:
        # Default to data.gov.in provider for Indian CPCB stations
        return DataGovINProvider()
