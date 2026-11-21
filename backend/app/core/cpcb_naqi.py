"""Central Pollution Control Board (CPCB) National Air Quality Index (NAQI) Calculation Engine.

Source of Truth:
Official CPCB 2014 Report: "National Air Quality Index" (CPCB / MoEF&CC / IIT Kanpur, October 2014)
Reference Documents:
  - https://airquality.cpcb.gov.in/ccr_docs/FINAL-REPORT_AQI_.pdf
  - https://www.airquality.cpcb.gov.in/ccr_docs/How_AQI_Calculated.pdf

Methodology:
1. Piecewise Linear Segmented Principle (continuous function, sub-index 0-400):
   I_p = [ (I_HI - I_LO) / (B_HI - B_LO) ] * (C_p - B_LO) + I_LO
   where:
     C_p  = pollutant concentration (time-averaged)
     B_HI = breakpoint concentration >= C_p
     B_LO = breakpoint concentration <= C_p
     I_HI = AQI sub-index value corresponding to B_HI
     I_LO = AQI sub-index value corresponding to B_LO

   The breakpoint table is structured so that I_HI of segment k equals I_LO
   of segment k+1, ensuring a continuous piecewise linear function. The
   displayed CPCB ranges (0-50, 51-100, ...) denote category integer ranges,
   but the interpolation formula uses the boundary values (0, 50, 100, 200,
   300, 400, 500) for continuity.

2. Severe Category (sub-index 401-500):
   The official CPCB breakpoint table defines the Severe range as open-ended
   (e.g., PM2.5 >= 250, PM10 >= 430). There is NO published upper
   concentration boundary (B_HI) for the Severe category.

   Consequence: standard linear interpolation CANNOT produce a specific
   numeric sub-index between 401 and 500 for concentrations in the Severe
   range because the formula requires a finite B_HI.

   Our approach: When a concentration falls in the Severe range (above the
   Very Poor upper boundary), we report:
     - sub_index = None (not exactly determinable)
     - sub_index_lower_bound = 401 (first integer in Severe category)
     - sub_index_upper_bound = 500 (scale maximum)
     - is_exact = False
     - category = "Severe"
     - A note explaining why the exact sub-index is not determinable.

   This avoids fabricating numbers that the official methodology does not
   support, and prevents downstream consumers from treating a range as
   an exact measurement.

   Note on O3: The CPCB 2014 report includes a footnote that O3
   concentrations reaching the Severe range (>= 748 ug/m3 for 8-hr average)
   would be "atypically high" under ambient conditions.

3. Data Requirements:
   - Minimum 16 hours of qualifying monitoring data required for valid
     sub-index calculation, as stated in CPCB methodology.
   - This applies uniformly to all pollutants regardless of averaging period.
   - Averaging periods: 24 hours for PM2.5, PM10, NO2, SO2, NH3, Pb;
     8 hours for CO and O3.

4. Overall AQI Rules:
   - Minimum 3 valid pollutant sub-indices required.
   - At least one mandatory particulate sub-index (PM2.5 or PM10).
   - Overall AQI = max(valid sub-indices) when all are exact.
   - When the dominant pollutant is in the Severe range, the overall AQI
     is also reported as a range (401-500), not an exact number.
   - Dominant / Prominent Pollutant = pollutant yielding the maximum
     sub-index (or maximum lower_bound when ranges are involved).

5. Scale Boundaries:
   - Defined scale range: 0 to 500. No extrapolation beyond 500.

6. Rounding:
   Sub-indices are rounded to the nearest integer using arithmetic
   round-half-up: math.floor(x + 0.5) for non-negative values.
   This is the conventional mathematical default. The CPCB report does
   not specify a rounding convention; we do not claim this is an official
   CPCB rule.
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Dict, List, Optional, Tuple


class PollutantType(str, Enum):
    PM25 = "PM2.5"
    PM10 = "PM10"
    NO2 = "NO2"
    SO2 = "SO2"
    CO = "CO"
    O3 = "O3"
    NH3 = "NH3"
    PB = "Pb"


class AQICategory(str, Enum):
    GOOD = "Good"
    SATISFACTORY = "Satisfactory"
    MODERATE = "Moderate"
    POOR = "Poor"
    VERY_POOR = "Very Poor"
    SEVERE = "Severe"
    UNKNOWN = "Unknown"


# Standard units per CPCB NAAQS (National Ambient Air Quality Standards)
STANDARD_POLLUTANT_UNITS: Dict[PollutantType, List[str]] = {
    PollutantType.PM25: ["µg/m³", "ug/m3", "µg/m3", "ug/m^3", "µg/m^3"],
    PollutantType.PM10: ["µg/m³", "ug/m3", "µg/m3", "ug/m^3", "µg/m^3"],
    PollutantType.NO2: ["µg/m³", "ug/m3", "µg/m3", "ug/m^3", "µg/m^3"],
    PollutantType.SO2: ["µg/m³", "ug/m3", "µg/m3", "ug/m^3", "µg/m^3"],
    PollutantType.CO: ["mg/m³", "mg/m3", "mg/m^3"],
    PollutantType.O3: ["µg/m³", "ug/m3", "µg/m3", "ug/m^3", "µg/m^3"],
    PollutantType.NH3: ["µg/m³", "ug/m3", "µg/m3", "ug/m^3", "µg/m^3"],
    PollutantType.PB: ["µg/m³", "ug/m3", "µg/m3", "ug/m^3", "µg/m^3"],
}

# Standard averaging periods (hours) per CPCB
POLLUTANT_AVERAGING_HOURS: Dict[PollutantType, int] = {
    PollutantType.PM25: 24,
    PollutantType.PM10: 24,
    PollutantType.NO2: 24,
    PollutantType.SO2: 24,
    PollutantType.CO: 8,
    PollutantType.O3: 8,
    PollutantType.NH3: 24,
    PollutantType.PB: 24,
}

# Minimum qualifying monitoring hours required for valid sub-index calculation.
# CPCB methodology states minimum 16 hours for valid sub-index, applied
# uniformly to all pollutants regardless of averaging period.
POLLUTANT_MIN_HOURS: Dict[PollutantType, float] = {
    PollutantType.PM25: 16.0,
    PollutantType.PM10: 16.0,
    PollutantType.NO2: 16.0,
    PollutantType.SO2: 16.0,
    PollutantType.CO: 16.0,
    PollutantType.O3: 16.0,
    PollutantType.NH3: 16.0,
    PollutantType.PB: 16.0,
}


@dataclass(frozen=True)
class Breakpoint:
    """A single row of the CPCB breakpoint table.

    b_hi is None for the Severe category, since the official CPCB table
    does not define an upper concentration boundary for Severe.

    i_lo and i_hi use continuous boundary values (not displayed range values)
    to ensure the piecewise linear function is continuous at breakpoints.
    """
    b_lo: float
    b_hi: Optional[float]  # None = open-ended (Severe range)
    i_lo: int
    i_hi: int
    category: AQICategory


@dataclass(frozen=True)
class SubIndexValue:
    """Represents a validated sub-index: exact value (Good-Very Poor) or range (Severe).

    Used internally for overall AQI calculation.
    """
    lower_bound: int    # Exact value, or 401 for Severe
    upper_bound: int    # Exact value, or 500 for Severe
    is_exact: bool      # True for Good-Very Poor, False for Severe


# Official CPCB Breakpoints Table (October 2014)
#
# B_LO, B_HI are concentration boundaries; I_LO, I_HI are sub-index
# boundary values chosen for piecewise linear continuity.
#
# The displayed CPCB categories show integer ranges like 0-50, 51-100, etc.
# For the interpolation formula, the boundary values are:
#   Good:         I = [0, 50]
#   Satisfactory: I = [50, 100]
#   Moderate:     I = [100, 200]
#   Poor:         I = [200, 300]
#   Very Poor:    I = [300, 400]
#   Severe:       I = [400, 500]  (open-ended concentration)
#
# This ensures I_HI(k) = I_LO(k+1) at every breakpoint transition.
#
# Severe ranges have b_hi=None because the official table is open-ended.
# Pollutant concentration thresholds for Severe entry:
#   PM2.5 >= 250 µg/m³,  PM10 >= 430 µg/m³,  NO2 >= 400 µg/m³,
#   SO2 >= 1600 µg/m³,   CO >= 34 mg/m³,      O3 >= 748 µg/m³*,
#   NH3 >= 1800 µg/m³,   Pb >= 3.5 µg/m³
#
# * O3 footnote: 8-hr average concentrations >= 748 µg/m³ would be
#   atypically high under normal ambient conditions (CPCB 2014 report).

CPCB_BREAKPOINTS: Dict[PollutantType, List[Breakpoint]] = {
    PollutantType.PM25: [
        Breakpoint(0.0, 30.0, 0, 50, AQICategory.GOOD),
        Breakpoint(30.0, 60.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(60.0, 90.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(90.0, 120.0, 200, 300, AQICategory.POOR),
        Breakpoint(120.0, 250.0, 300, 400, AQICategory.VERY_POOR),
        Breakpoint(250.0, None, 400, 500, AQICategory.SEVERE),
    ],
    PollutantType.PM10: [
        Breakpoint(0.0, 50.0, 0, 50, AQICategory.GOOD),
        Breakpoint(50.0, 100.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(100.0, 250.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(250.0, 350.0, 200, 300, AQICategory.POOR),
        Breakpoint(350.0, 430.0, 300, 400, AQICategory.VERY_POOR),
        Breakpoint(430.0, None, 400, 500, AQICategory.SEVERE),
    ],
    PollutantType.NO2: [
        Breakpoint(0.0, 40.0, 0, 50, AQICategory.GOOD),
        Breakpoint(40.0, 80.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(80.0, 180.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(180.0, 280.0, 200, 300, AQICategory.POOR),
        Breakpoint(280.0, 400.0, 300, 400, AQICategory.VERY_POOR),
        Breakpoint(400.0, None, 400, 500, AQICategory.SEVERE),
    ],
    PollutantType.SO2: [
        Breakpoint(0.0, 40.0, 0, 50, AQICategory.GOOD),
        Breakpoint(40.0, 80.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(80.0, 380.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(380.0, 800.0, 200, 300, AQICategory.POOR),
        Breakpoint(800.0, 1600.0, 300, 400, AQICategory.VERY_POOR),
        Breakpoint(1600.0, None, 400, 500, AQICategory.SEVERE),
    ],
    PollutantType.CO: [
        Breakpoint(0.0, 1.0, 0, 50, AQICategory.GOOD),
        Breakpoint(1.0, 2.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(2.0, 10.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(10.0, 17.0, 200, 300, AQICategory.POOR),
        Breakpoint(17.0, 34.0, 300, 400, AQICategory.VERY_POOR),
        Breakpoint(34.0, None, 400, 500, AQICategory.SEVERE),
    ],
    PollutantType.O3: [
        Breakpoint(0.0, 50.0, 0, 50, AQICategory.GOOD),
        Breakpoint(50.0, 100.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(100.0, 168.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(168.0, 208.0, 200, 300, AQICategory.POOR),
        Breakpoint(208.0, 748.0, 300, 400, AQICategory.VERY_POOR),
        # O3 footnote: 8-hr average >= 748 µg/m³ is atypically high
        # under normal ambient conditions (CPCB 2014 report).
        Breakpoint(748.0, None, 400, 500, AQICategory.SEVERE),
    ],
    PollutantType.NH3: [
        Breakpoint(0.0, 200.0, 0, 50, AQICategory.GOOD),
        Breakpoint(200.0, 400.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(400.0, 800.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(800.0, 1200.0, 200, 300, AQICategory.POOR),
        Breakpoint(1200.0, 1800.0, 300, 400, AQICategory.VERY_POOR),
        Breakpoint(1800.0, None, 400, 500, AQICategory.SEVERE),
    ],
    PollutantType.PB: [
        Breakpoint(0.0, 0.5, 0, 50, AQICategory.GOOD),
        Breakpoint(0.5, 1.0, 50, 100, AQICategory.SATISFACTORY),
        Breakpoint(1.0, 2.0, 100, 200, AQICategory.MODERATE),
        Breakpoint(2.0, 3.0, 200, 300, AQICategory.POOR),
        Breakpoint(3.0, 3.5, 300, 400, AQICategory.VERY_POOR),
        Breakpoint(3.5, None, 400, 500, AQICategory.SEVERE),
    ],
}

# O3 Severe footnote text, available for downstream consumers.
O3_SEVERE_FOOTNOTE = (
    "CPCB 2014 Report footnote: 8-hour average O3 concentrations reaching "
    "the Severe range (>= 748 µg/m³) would be atypically high under normal "
    "ambient conditions."
)


def _round_half_up(x: float) -> int:
    """Round to nearest integer with round-half-up convention.

    Standard arithmetic rounding: when the fractional part is exactly 0.5,
    round up (away from zero for positive values).

    Used because the CPCB methodology does not specify a rounding convention,
    and round-half-up is the conventional mathematical default. We do not
    claim this is an official CPCB rule.

    Valid only for non-negative values (sub-indices are always >= 0).
    """
    return math.floor(x + 0.5)


def normalize_pollutant_type(pollutant: str) -> Optional[PollutantType]:
    """Resolve raw string name to PollutantType enum case-insensitively."""
    cleaned = pollutant.strip().upper()
    mapping = {
        "PM2.5": PollutantType.PM25,
        "PM25": PollutantType.PM25,
        "PM10": PollutantType.PM10,
        "NO2": PollutantType.NO2,
        "SO2": PollutantType.SO2,
        "CO": PollutantType.CO,
        "O3": PollutantType.O3,
        "OZONE": PollutantType.O3,
        "NH3": PollutantType.NH3,
        "PB": PollutantType.PB,
        "LEAD": PollutantType.PB,
    }
    return mapping.get(cleaned)


def validate_measurement_input(
    pollutant: PollutantType,
    concentration: float,
    unit: str,
    hours_recorded: Optional[float] = 24.0,
) -> Tuple[bool, Optional[str]]:
    """Validate concentration sanity, unit compatibility, and data capture hours."""
    # 1. Non-finite or negative checks
    if concentration is None or math.isnan(concentration) or math.isinf(concentration):
        return False, f"Invalid concentration: value must be a real finite number (got {concentration})"

    if concentration < 0.0:
        return False, f"Invalid concentration: negative values are physically impossible (got {concentration})"

    # 2. Unit verification
    valid_units = STANDARD_POLLUTANT_UNITS.get(pollutant, [])
    cleaned_unit = unit.strip().replace(" ", "").lower()
    normalized_valid = [u.replace(" ", "").lower() for u in valid_units]

    if cleaned_unit not in normalized_valid:
        expected = valid_units[0]
        return False, f"Incorrect unit for {pollutant.value}: expected '{expected}' (got '{unit}')"

    # 3. Minimum hours recorded validation (16 hours for all pollutants per CPCB)
    min_required_hours = POLLUTANT_MIN_HOURS.get(pollutant, 16.0)
    avg_period = POLLUTANT_AVERAGING_HOURS.get(pollutant, 24)

    if hours_recorded is None:
        return False, (
            f"Missing or undocumented monitoring duration for {pollutant.value}: "
            f"CPCB requires verified minimum {min_required_hours:.1f} hours of qualifying data for a {avg_period}-hr average."
        )

    if hours_recorded < min_required_hours:
        return False, (
            f"Insufficient monitoring duration for {pollutant.value}: recorded {hours_recorded:.1f} hours, "
            f"minimum {min_required_hours:.1f} hours required for a valid {avg_period}-hr average."
        )

    return True, None


def find_breakpoint(pollutant: PollutantType, concentration: float) -> Optional[Breakpoint]:
    """Locate the bounding CPCB breakpoint row for a given pollutant concentration.

    For the Severe row (open-ended), matches any concentration > b_lo of
    the previous segment's upper boundary (i.e., strictly above Very Poor).
    At exactly the boundary value, the concentration falls in Very Poor
    (b_lo < C <= b_hi), producing sub-index 400.
    """
    breakpoints = CPCB_BREAKPOINTS.get(pollutant, [])
    if not breakpoints:
        return None

    # Handle boundary exact match for 0
    if concentration == 0.0:
        return breakpoints[0]

    for bp in breakpoints:
        if bp.b_hi is None:
            # Open-ended Severe range: matches anything > b_lo
            # (At exactly b_lo, the previous segment's b_hi matches.)
            if concentration > bp.b_lo:
                return bp
        elif bp == breakpoints[0]:
            # First bracket: b_lo <= C <= b_hi (inclusive both ends)
            if bp.b_lo <= concentration <= bp.b_hi:
                return bp
        else:
            # Subsequent brackets: b_lo < C <= b_hi
            if bp.b_lo < concentration <= bp.b_hi:
                return bp

    return None


def calculate_sub_index(
    pollutant: PollutantType,
    concentration: float,
    unit: str,
    hours_recorded: Optional[float] = 24.0,
) -> Tuple[Optional[int], AQICategory, Optional[str], Optional[str]]:
    """Calculate the CPCB AQI sub-index using piecewise linear interpolation.

    Returns:
        (sub_index, category, error_message, note)

    For concentrations in the Severe range (open-ended breakpoint), sub_index
    is None because the exact value is not determinable. The caller should use
    the category to infer the range (401-500).
    """
    is_valid, error = validate_measurement_input(pollutant, concentration, unit, hours_recorded)
    if not is_valid:
        return None, AQICategory.UNKNOWN, error, None

    bp = find_breakpoint(pollutant, concentration)
    if not bp:
        return None, AQICategory.UNKNOWN, f"No breakpoint bracket found for {pollutant.value} at {concentration}", None

    note = None

    if bp.b_hi is None:
        # Severe range: open-ended, no upper breakpoint for interpolation.
        # Cannot determine exact sub-index; report as None with Severe category.
        note = (
            f"Severe category; exact sub-index is not determinable from "
            f"open-ended published concentration breakpoints. Concentration "
            f"{concentration} {unit} exceeds the Severe threshold "
            f"(>= {bp.b_lo} {unit} for {pollutant.value}). The sub-index "
            f"falls in the range 401-500."
        )
        # Add O3 footnote if applicable
        if pollutant == PollutantType.O3:
            note += f" {O3_SEVERE_FOOTNOTE}"
        return None, AQICategory.SEVERE, None, note
    else:
        # Standard interpolation for ranges Good through Very Poor (0-400)
        denominator = bp.b_hi - bp.b_lo
        if denominator == 0:
            # Degenerate bracket (should not occur with valid CPCB tables)
            sub_index = bp.i_lo
        else:
            slope = (bp.i_hi - bp.i_lo) / denominator
            raw_index = slope * (concentration - bp.b_lo) + bp.i_lo
            sub_index = _round_half_up(raw_index)

        # Strict bounds: 0 <= sub_index <= 500
        sub_index = max(0, min(500, sub_index))
        category = get_category_for_index(sub_index)

        return sub_index, category, None, None


def get_category_for_index(aqi: int) -> AQICategory:
    """Classify AQI integer (0-500) into CPCB official health categories."""
    if aqi < 0:
        return AQICategory.UNKNOWN
    if aqi <= 50:
        return AQICategory.GOOD
    if aqi <= 100:
        return AQICategory.SATISFACTORY
    if aqi <= 200:
        return AQICategory.MODERATE
    if aqi <= 300:
        return AQICategory.POOR
    if aqi <= 400:
        return AQICategory.VERY_POOR
    return AQICategory.SEVERE


def calculate_overall_aqi(
    sub_indices: Dict[PollutantType, SubIndexValue]
) -> dict:
    """Calculate overall station AQI following official CPCB validation rules.

    CPCB Criteria:
    1. Minimum 3 valid pollutant sub-indices required (N >= 3).
    2. At least one must be a particulate (PM2.5 or PM10).
    3. Overall AQI = max(valid sub-indices) when all are exact.
    4. When the dominant pollutant is Severe (not exact), the overall AQI
       is reported as a range (401-500), not an exact number.
    5. Dominant Pollutant = pollutant with max sub-index (or max lower_bound).

    Returns:
        dict with keys: overall_aqi, overall_aqi_lower_bound,
        overall_aqi_upper_bound, is_exact, category, dominant_pollutant,
        reason, is_eligible
    """
    _unavailable = {
        "overall_aqi": None,
        "overall_aqi_lower_bound": None,
        "overall_aqi_upper_bound": None,
        "is_exact": False,
        "category": AQICategory.UNKNOWN,
        "dominant_pollutant": None,
        "is_eligible": False,
    }

    # Rule 1: Check minimum 3 pollutants
    valid_count = len(sub_indices)
    if valid_count < 3:
        return {
            **_unavailable,
            "reason": (
                f"Insufficient pollutant coverage: CPCB requires data for "
                f"at least 3 pollutants (available: {valid_count})"
            ),
        }

    # Rule 2: Check mandatory particulate requirement (PM2.5 or PM10)
    has_pm25 = PollutantType.PM25 in sub_indices
    has_pm10 = PollutantType.PM10 in sub_indices
    if not (has_pm25 or has_pm10):
        return {
            **_unavailable,
            "reason": (
                "Mandatory particulate requirement not met: at least one "
                "of PM2.5 or PM10 must be valid"
            ),
        }

    # Rule 3-5: Find dominant pollutant by maximum lower_bound
    dominant = max(sub_indices, key=lambda p: sub_indices[p].lower_bound)
    dominant_data = sub_indices[dominant]

    if dominant_data.is_exact:
        overall_aqi = dominant_data.lower_bound
        overall_lb = overall_aqi
        overall_ub = overall_aqi
        is_exact = True
    else:
        # Severe dominant: overall is a range, not an exact number
        overall_aqi = None
        overall_lb = dominant_data.lower_bound   # 401
        overall_ub = dominant_data.upper_bound    # 500
        is_exact = False

    category = get_category_for_index(overall_lb)

    return {
        "overall_aqi": overall_aqi,
        "overall_aqi_lower_bound": overall_lb,
        "overall_aqi_upper_bound": overall_ub,
        "is_exact": is_exact,
        "category": category,
        "dominant_pollutant": dominant,
        "reason": f"Overall AQI successfully calculated (Dominant: {dominant.value})",
        "is_eligible": True,
    }


def compute_station_cpcb_aqi(measurements: list) -> dict:
    """Orchestrate end-to-end evaluation of raw measurements into CPCB sub-indices and overall AQI.

    Input can be a list of PollutantMeasurement objects or plain dicts.
    Returns a dictionary structure compatible with OverallAQIResult schema.
    """
    from datetime import datetime, timezone

    evaluated_sub_indices: Dict[str, dict] = {}
    valid_sub_index_data: Dict[PollutantType, SubIndexValue] = {}

    for item in measurements:
        # Extract attributes from model or dict
        if hasattr(item, "pollutant"):
            p_name = item.pollutant
            c_val = item.value
            u_str = item.unit
            avg_hrs = getattr(item, "averaging_hours", getattr(item, "averaging_period_hours", 24))
            rec_hrs = getattr(item, "hours_recorded", getattr(item, "coverage_hours", None))
        else:
            p_name = item.get("pollutant", "")
            c_val = item.get("value", 0.0)
            u_str = item.get("unit", "")
            avg_hrs = item.get("averaging_hours", item.get("averaging_period_hours", 24))
            rec_hrs = item.get("hours_recorded", item.get("coverage_hours", None))

        p_type = normalize_pollutant_type(p_name)
        if not p_type:
            evaluated_sub_indices[p_name] = {
                "pollutant": p_name,
                "concentration": c_val,
                "unit": u_str,
                "averaging_hours": avg_hrs,
                "hours_recorded": rec_hrs,
                "sub_index": None,
                "sub_index_lower_bound": None,
                "sub_index_upper_bound": None,
                "is_exact": False,
                "category": AQICategory.UNKNOWN.value,
                "is_valid": False,
                "validation_error": f"Unrecognized CPCB criteria pollutant: '{p_name}'",
                "note": None,
            }
            continue

        standard_avg = POLLUTANT_AVERAGING_HOURS.get(p_type, avg_hrs)
        sub_idx, cat, error, note = calculate_sub_index(p_type, c_val, u_str, rec_hrs)
        is_valid = error is None

        if is_valid:
            if cat == AQICategory.SEVERE:
                # Severe: not exactly determinable
                sub_idx_lb = 401
                sub_idx_ub = 500
                is_exact = False
                valid_sub_index_data[p_type] = SubIndexValue(401, 500, False)
            else:
                # Good through Very Poor: exact interpolated value
                sub_idx_lb = sub_idx
                sub_idx_ub = sub_idx
                is_exact = True
                valid_sub_index_data[p_type] = SubIndexValue(sub_idx, sub_idx, True)
        else:
            sub_idx_lb = None
            sub_idx_ub = None
            is_exact = False

        evaluated_sub_indices[p_type.value] = {
            "pollutant": p_type.value,
            "concentration": c_val,
            "unit": u_str,
            "averaging_hours": standard_avg,
            "hours_recorded": rec_hrs,
            "sub_index": sub_idx,
            "sub_index_lower_bound": sub_idx_lb,
            "sub_index_upper_bound": sub_idx_ub,
            "is_exact": is_exact,
            "category": cat.value,
            "is_valid": is_valid,
            "validation_error": error,
            "note": note,
        }

    overall = calculate_overall_aqi(valid_sub_index_data)
    has_pm = (PollutantType.PM25 in valid_sub_index_data) or (
        PollutantType.PM10 in valid_sub_index_data
    )

    return {
        "overall_aqi": overall["overall_aqi"],
        "overall_aqi_lower_bound": overall["overall_aqi_lower_bound"],
        "overall_aqi_upper_bound": overall["overall_aqi_upper_bound"],
        "is_exact": overall["is_exact"],
        "category": overall["category"].value,
        "dominant_pollutant": overall["dominant_pollutant"].value if overall["dominant_pollutant"] else None,
        "status": "CALCULATED" if overall["is_eligible"] else "UNAVAILABLE",
        "reason": overall["reason"],
        "eligible_for_overall_aqi": overall["is_eligible"],
        "valid_pollutants_count": len(valid_sub_index_data),
        "has_mandatory_pm": has_pm,
        "sub_indices": evaluated_sub_indices,
        "timestamp_utc": datetime.now(timezone.utc),
    }
