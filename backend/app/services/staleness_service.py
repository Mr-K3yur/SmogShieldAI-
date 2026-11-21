"""Staleness Service for SmogShield AI.

Handles timezone-aware timestamp normalization, local Indian Standard Time
(Asia/Kolkata) formatting, future-timestamp rejection, and freshness classification
against application policy.

Application Freshness Policy:
- FRESH:   Age <= 4.0 hours
- STALE:   4.0 hours < Age <= 24.0 hours (measurements remain visible with warning)
- EXPIRED: Age > 24.0 hours (never called live; marked UNAVAILABLE)
- DEMO:    Explicitly enabled mock/demo data

Note: These are application operational policies, not official CPCB safety thresholds.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from app.schemas.station import FreshnessType

try:
    from zoneinfo import ZoneInfo
    INDIA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    INDIA_TZ = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")

# Maximum future clock drift tolerated before rejection (5 minutes)
MAX_FUTURE_TOLERANCE_SECONDS = 300.0


def to_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware and converted to UTC."""
    if dt.tzinfo is None:
        # If naive, assume UTC as standard storage format
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_ist_string(dt_utc: Optional[datetime], fmt: str = "%d %b %Y, %I:%M %p IST") -> Optional[str]:
    """Convert a UTC datetime to formatted local Indian Standard Time string."""
    if dt_utc is None:
        return None
    aware_utc = to_utc(dt_utc)
    ist_time = aware_utc.astimezone(INDIA_TZ)
    return ist_time.strftime(fmt)


def evaluate_freshness(
    observed_at: Optional[datetime],
    now_utc: Optional[datetime] = None,
    fresh_hours: float = 4.0,
    stale_hours: float = 24.0,
    is_demo: bool = False,
) -> Tuple[FreshnessType, Optional[str]]:
    """Evaluate data freshness against application policy thresholds.

    Returns:
        (FreshnessType, warning_or_error_message)
    """
    if is_demo:
        return FreshnessType.DEMO, "SIMULATED DATA - NOT LIVE AQI"

    if observed_at is None:
        return FreshnessType.UNKNOWN, "No observation timestamp provided by sensor"

    current_time = to_utc(now_utc) if now_utc is not None else datetime.now(timezone.utc)
    obs_time = to_utc(observed_at)

    # 1. Detect future timestamp (clock drift beyond tolerance)
    time_diff = (obs_time - current_time).total_seconds()
    if time_diff > MAX_FUTURE_TOLERANCE_SECONDS:
        future_minutes = round(time_diff / 60.0, 1)
        return (
            FreshnessType.UNKNOWN,
            f"Invalid timestamp: reading is from the future ({future_minutes} min ahead of current UTC time). Sensor clock drift detected."
        )

    # 2. Compute observation age in hours
    age_seconds = (current_time - obs_time).total_seconds()
    if age_seconds < 0:
        # Minor positive drift within tolerance (e.g. 10 seconds), treat as fresh
        age_hours = 0.0
    else:
        age_hours = age_seconds / 3600.0

    # 3. Classify against application policy
    if age_hours <= fresh_hours:
        return FreshnessType.FRESH, None
    elif age_hours <= stale_hours:
        age_formatted = f"{age_hours:.1f} hours" if age_hours < 10 else f"{int(round(age_hours))} hours"
        return (
            FreshnessType.STALE,
            f"Data is STALE: observed {age_formatted} ago (exceeds {fresh_hours:.0f}-hour fresh threshold). Measurements remain visible for guidance."
        )
    else:
        age_formatted = f"{int(round(age_hours))} hours"
        return (
            FreshnessType.EXPIRED,
            f"Data is EXPIRED: observed {age_formatted} ago (exceeds {stale_hours:.0f}-hour operational limit). Cannot be used as live AQI."
        )
