"""Comprehensive tests for the CPCB National AQI Calculation Engine.

All reference values are derived from the official CPCB 2014 breakpoint
table using the published linear interpolation formula with continuous
boundary values:
  I_p = [(I_HI - I_LO) / (B_HI - B_LO)] * (C_p - B_LO) + I_LO

Rounding: round-half-up via math.floor(x + 0.5). The CPCB report does
not specify a rounding convention; we use the conventional mathematical
default and do not claim it is an official CPCB rule.
"""

import math
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.cpcb_naqi import (
    PollutantType,
    AQICategory,
    SubIndexValue,
    calculate_sub_index,
    calculate_overall_aqi,
    get_category_for_index,
    find_breakpoint,
    validate_measurement_input,
    compute_station_cpcb_aqi,
    CPCB_BREAKPOINTS,
    POLLUTANT_MIN_HOURS,
    O3_SEVERE_FOOTNOTE,
    _round_half_up,
)


# =====================================================================
# 1. PM2.5 BREAKPOINT TESTS (continuous breakpoints)
# =====================================================================

class TestPM25:
    """PM2.5: [0,30]→[0,50], [30,60]→[50,100], [60,90]→[100,200],
    [90,120]→[200,300], [120,250]→[300,400], [250+]→Severe"""

    def test_good_lower(self):
        idx, cat, err, note = calculate_sub_index(PollutantType.PM25, 0.0, "µg/m³", 24.0)
        assert idx == 0 and cat == AQICategory.GOOD and err is None and note is None

    def test_good_mid(self):
        # slope = 50/30; 50/30 * 15 + 0 = 25.0
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 15.0, "µg/m³", 24.0)
        assert idx == 25 and cat == AQICategory.GOOD and err is None

    def test_good_upper(self):
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 30.0, "µg/m³", 24.0)
        assert idx == 50 and cat == AQICategory.GOOD and err is None

    def test_satisfactory_mid(self):
        # [30,60]→[50,100]; slope = 50/30 = 5/3; 5/3 * 15 + 50 = 75.0
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 45.0, "µg/m³", 24.0)
        assert idx == 75 and cat == AQICategory.SATISFACTORY and err is None

    def test_satisfactory_upper(self):
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 60.0, "µg/m³", 24.0)
        assert idx == 100 and cat == AQICategory.SATISFACTORY and err is None

    def test_moderate_upper(self):
        # [60,90]→[100,200]; slope = 100/30; 100/30 * 30 + 100 = 200
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 90.0, "µg/m³", 24.0)
        assert idx == 200 and cat == AQICategory.MODERATE and err is None

    def test_poor_upper(self):
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 120.0, "µg/m³", 24.0)
        assert idx == 300 and cat == AQICategory.POOR and err is None

    def test_very_poor_upper(self):
        # [120,250]→[300,400]; slope = 100/130; 100/130 * 130 + 300 = 400
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 250.0, "µg/m³", 24.0)
        assert idx == 400 and cat == AQICategory.VERY_POOR and err is None

    def test_reference_pm25_160(self):
        """User reference: PM2.5 = 160 → ~331.
        [120,250]→[300,400]; slope = 100/130; 100/130 * 40 + 300 = 330.769 → 331
        """
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 160.0, "µg/m³", 24.0)
        assert idx == 331 and cat == AQICategory.VERY_POOR and err is None

    def test_severe_just_above_threshold(self):
        """PM2.5 > 250: Severe with sub_index None."""
        idx, cat, err, note = calculate_sub_index(PollutantType.PM25, 250.1, "µg/m³", 24.0)
        assert idx is None and cat == AQICategory.SEVERE and err is None
        assert note is not None and "Severe" in note

    def test_severe_high_concentration(self):
        idx, cat, err, note = calculate_sub_index(PollutantType.PM25, 380.0, "µg/m³", 24.0)
        assert idx is None and cat == AQICategory.SEVERE and err is None
        assert note is not None

    def test_severe_extreme(self):
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, 650.0, "µg/m³", 24.0)
        assert idx is None and cat == AQICategory.SEVERE and err is None


# =====================================================================
# 2. PM10 BREAKPOINT TESTS
# =====================================================================

class TestPM10:
    """PM10: [0,50]→[0,50], [50,100]→[50,100], [100,250]→[100,200],
    [250,350]→[200,300], [350,430]→[300,400], [430+]→Severe"""

    def test_good_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 50.0, "µg/m³")
        assert idx == 50 and cat == AQICategory.GOOD

    def test_satisfactory_mid(self):
        # [50,100]→[50,100]; slope = 50/50 = 1; 1 * 25 + 50 = 75
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 75.0, "µg/m³")
        assert idx == 75 and cat == AQICategory.SATISFACTORY

    def test_moderate_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 250.0, "µg/m³")
        assert idx == 200 and cat == AQICategory.MODERATE

    def test_reference_pm10_280(self):
        """User reference: PM10 = 280 → 230.
        [250,350]→[200,300]; slope = 100/100 = 1; 1 * 30 + 200 = 230
        """
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 280.0, "µg/m³")
        assert idx == 230 and cat == AQICategory.POOR

    def test_poor_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 350.0, "µg/m³")
        assert idx == 300 and cat == AQICategory.POOR

    def test_very_poor_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 430.0, "µg/m³")
        assert idx == 400 and cat == AQICategory.VERY_POOR

    def test_severe_just_above(self):
        idx, cat, err, note = calculate_sub_index(PollutantType.PM10, 430.1, "µg/m³")
        assert idx is None and cat == AQICategory.SEVERE and err is None
        assert note is not None and "Severe" in note

    def test_severe_extreme(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 950.0, "µg/m³")
        assert idx is None and cat == AQICategory.SEVERE


# =====================================================================
# 3. GASEOUS POLLUTANT TESTS
# =====================================================================

class TestNO2:
    def test_good_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.NO2, 40.0, "µg/m³")
        assert idx == 50 and cat == AQICategory.GOOD

    def test_reference_no2_65(self):
        """User reference: NO2 = 65 → 81.
        [40,80]→[50,100]; slope = 50/40 = 1.25; 1.25 * 25 + 50 = 81.25 → 81
        """
        idx, cat, _, _ = calculate_sub_index(PollutantType.NO2, 65.0, "µg/m³")
        assert idx == 81 and cat == AQICategory.SATISFACTORY

    def test_severe(self):
        idx, cat, _, note = calculate_sub_index(PollutantType.NO2, 450.0, "µg/m³")
        assert idx is None and cat == AQICategory.SEVERE
        assert note is not None


class TestSO2:
    def test_good_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.SO2, 40.0, "µg/m³")
        assert idx == 50 and cat == AQICategory.GOOD

    def test_moderate_mid(self):
        # [80,380]→[100,200]; slope = 100/300 = 1/3; 1/3 * 150 + 100 = 150.0
        idx, cat, _, _ = calculate_sub_index(PollutantType.SO2, 230.0, "µg/m³")
        assert idx == 150 and cat == AQICategory.MODERATE

    def test_severe(self):
        idx, cat, _, note = calculate_sub_index(PollutantType.SO2, 2000.0, "µg/m³")
        assert idx is None and cat == AQICategory.SEVERE
        assert note is not None


class TestCO:
    def test_good_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.CO, 1.0, "mg/m³", hours_recorded=24.0)
        assert idx == 50 and cat == AQICategory.GOOD

    def test_satisfactory_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.CO, 2.0, "mg/m³", hours_recorded=24.0)
        assert idx == 100 and cat == AQICategory.SATISFACTORY

    def test_reference_co_1_8(self):
        """User reference: CO = 1.8 → 90.
        [1,2]→[50,100]; slope = 50; 50 * 0.8 + 50 = 90.0
        """
        idx, cat, _, _ = calculate_sub_index(PollutantType.CO, 1.8, "mg/m³", hours_recorded=24.0)
        assert idx == 90 and cat == AQICategory.SATISFACTORY

    def test_min_hours_16_required(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.CO, 1.5, "mg/m³", hours_recorded=15.9)
        assert idx is None
        assert "minimum 16.0 hours required" in err

    def test_min_hours_16_accepted(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.CO, 1.5, "mg/m³", hours_recorded=16.0)
        assert idx is not None and err is None

    def test_severe(self):
        idx, cat, _, note = calculate_sub_index(PollutantType.CO, 50.0, "mg/m³", hours_recorded=24.0)
        assert idx is None and cat == AQICategory.SEVERE
        assert note is not None


class TestO3:
    def test_good_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.O3, 50.0, "µg/m³", hours_recorded=24.0)
        assert idx == 50 and cat == AQICategory.GOOD

    def test_min_hours_16_required(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.O3, 50.0, "µg/m³", hours_recorded=15.9)
        assert idx is None
        assert "minimum 16.0 hours required" in err

    def test_min_hours_16_accepted(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.O3, 50.0, "µg/m³", hours_recorded=16.0)
        assert idx is not None and err is None

    def test_severe_with_footnote(self):
        idx, cat, err, note = calculate_sub_index(PollutantType.O3, 800.0, "µg/m³", hours_recorded=24.0)
        assert idx is None and cat == AQICategory.SEVERE and err is None
        assert note is not None
        assert "atypically high" in note


class TestNH3:
    def test_good_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.NH3, 200.0, "µg/m³")
        assert idx == 50 and cat == AQICategory.GOOD

    def test_severe(self):
        idx, cat, _, note = calculate_sub_index(PollutantType.NH3, 2000.0, "µg/m³")
        assert idx is None and cat == AQICategory.SEVERE
        assert note is not None


class TestPb:
    def test_good_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 0.5, "µg/m³")
        assert idx == 50 and cat == AQICategory.GOOD

    def test_satisfactory_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 1.0, "µg/m³")
        assert idx == 100 and cat == AQICategory.SATISFACTORY

    def test_moderate_mid(self):
        # [1.0,2.0]→[100,200]; slope = 100; 100 * 0.5 + 100 = 150
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 1.5, "µg/m³")
        assert idx == 150 and cat == AQICategory.MODERATE

    def test_poor_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 3.0, "µg/m³")
        assert idx == 300 and cat == AQICategory.POOR

    def test_very_poor_upper(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 3.5, "µg/m³")
        assert idx == 400 and cat == AQICategory.VERY_POOR

    def test_severe(self):
        idx, cat, _, note = calculate_sub_index(PollutantType.PB, 4.0, "µg/m³")
        assert idx is None and cat == AQICategory.SEVERE
        assert note is not None

    def test_severe_extreme(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 10.0, "µg/m³")
        assert idx is None and cat == AQICategory.SEVERE

    def test_decimal_value(self):
        # [0,0.5]→[0,50]; slope = 100; 100 * 0.25 = 25
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 0.25, "µg/m³")
        assert idx == 25 and cat == AQICategory.GOOD

    def test_decimal_boundary(self):
        # [2.0,3.0]→[200,300]; slope = 100; 100 * 0.5 + 200 = 250
        idx, cat, _, _ = calculate_sub_index(PollutantType.PB, 2.5, "µg/m³")
        assert idx == 250 and cat == AQICategory.POOR


# =====================================================================
# 4. SEVERE RANGE STRUCTURAL VERIFICATION
# =====================================================================

class TestSevereOpenEnded:
    """Verify that every pollutant's Severe breakpoint has b_hi=None."""

    def test_all_severe_breakpoints_open_ended(self):
        for pollutant, breakpoints in CPCB_BREAKPOINTS.items():
            severe_bp = breakpoints[-1]
            assert severe_bp.category == AQICategory.SEVERE, (
                f"{pollutant.value}: last breakpoint is not Severe"
            )
            assert severe_bp.b_hi is None, (
                f"{pollutant.value}: Severe b_hi should be None (open-ended), "
                f"got {severe_bp.b_hi}"
            )

    def test_severe_thresholds(self):
        """Verify the lower bounds of the Severe range match CPCB 2014 table."""
        expected_severe_b_lo = {
            PollutantType.PM25: 250.0,
            PollutantType.PM10: 430.0,
            PollutantType.NO2: 400.0,
            PollutantType.SO2: 1600.0,
            PollutantType.CO: 34.0,
            PollutantType.O3: 748.0,
            PollutantType.NH3: 1800.0,
            PollutantType.PB: 3.5,
        }
        for pollutant, expected_b_lo in expected_severe_b_lo.items():
            severe_bp = CPCB_BREAKPOINTS[pollutant][-1]
            assert severe_bp.b_lo == expected_b_lo, (
                f"{pollutant.value}: Severe b_lo expected {expected_b_lo}, got {severe_bp.b_lo}"
            )


# =====================================================================
# 5. SEVERE REPRESENTATION TESTS
# =====================================================================

class TestSevereRepresentation:
    """Verify Severe sub-indices use range representation, not exact values."""

    def test_severe_sub_index_is_none(self):
        """Severe sub_index must be None, not 401 or any exact number."""
        idx, cat, err, note = calculate_sub_index(PollutantType.PM25, 300.0, "µg/m³")
        assert idx is None
        assert cat == AQICategory.SEVERE
        assert err is None
        assert note is not None

    def test_severe_orchestration_has_range_fields(self):
        """compute_station_cpcb_aqi must include range fields for Severe."""
        measurements = [
            {"pollutant": "PM2.5", "value": 300.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 200.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 50.0, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
        res = compute_station_cpcb_aqi(measurements)

        # PM2.5 at 300 is Severe
        pm25 = res["sub_indices"]["PM2.5"]
        assert pm25["sub_index"] is None
        assert pm25["sub_index_lower_bound"] == 401
        assert pm25["sub_index_upper_bound"] == 500
        assert pm25["is_exact"] is False
        assert pm25["is_valid"] is True
        assert pm25["category"] == "Severe"
        assert pm25["note"] is not None

        # PM10 at 200 is exact (Moderate)
        pm10 = res["sub_indices"]["PM10"]
        assert pm10["sub_index"] is not None
        assert pm10["sub_index_lower_bound"] == pm10["sub_index"]
        assert pm10["sub_index_upper_bound"] == pm10["sub_index"]
        assert pm10["is_exact"] is True

    def test_severe_overall_aqi_is_range(self):
        """When dominant is Severe, overall_aqi is None with range bounds."""
        measurements = [
            {"pollutant": "PM2.5", "value": 300.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 200.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 50.0, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
        res = compute_station_cpcb_aqi(measurements)
        assert res["status"] == "CALCULATED"
        assert res["overall_aqi"] is None
        assert res["overall_aqi_lower_bound"] == 401
        assert res["overall_aqi_upper_bound"] == 500
        assert res["is_exact"] is False
        assert res["category"] == "Severe"

    def test_exact_overall_aqi_has_matching_bounds(self):
        """When all sub-indices are exact, overall_aqi equals bounds."""
        measurements = [
            {"pollutant": "PM2.5", "value": 160.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 200.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 50.0, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
        res = compute_station_cpcb_aqi(measurements)
        assert res["status"] == "CALCULATED"
        assert res["overall_aqi"] is not None
        assert res["overall_aqi"] == res["overall_aqi_lower_bound"]
        assert res["overall_aqi"] == res["overall_aqi_upper_bound"]
        assert res["is_exact"] is True


# =====================================================================
# 6. ROUNDING TESTS
# =====================================================================

class TestRounding:
    """Verify round-half-up convention and distinguish from banker's rounding."""

    def test_round_half_up_basic(self):
        assert _round_half_up(0.5) == 1
        assert _round_half_up(1.5) == 2
        assert _round_half_up(2.5) == 3
        assert _round_half_up(50.5) == 51
        assert _round_half_up(150.5) == 151
        assert _round_half_up(230.5) == 231

    def test_round_half_up_vs_bankers(self):
        """These cases distinguish round-half-up from banker's rounding.
        Banker's round(50.5) = 50 (even), round-half-up = 51.
        Banker's round(150.5) = 150 (even), round-half-up = 151.
        Banker's round(230.5) = 230 (even), round-half-up = 231.
        """
        # Verify our function differs from Python round() for these:
        assert _round_half_up(50.5) == 51
        assert round(50.5) == 50  # banker's gives 50
        assert _round_half_up(150.5) == 151
        assert round(150.5) == 150  # banker's gives 150
        assert _round_half_up(230.5) == 231
        assert round(230.5) == 230  # banker's gives 230

    def test_round_non_half_values(self):
        assert _round_half_up(0.0) == 0
        assert _round_half_up(0.4) == 0
        assert _round_half_up(0.6) == 1
        assert _round_half_up(75.0) == 75
        assert _round_half_up(75.3) == 75
        assert _round_half_up(75.7) == 76

    def test_half_value_in_interpolation_pm10(self):
        """PM10 = 280.5: [250,350]→[200,300]; slope=1; raw = 230.5 → 231.
        With banker's rounding this would be 230 (even).
        """
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 280.5, "µg/m³")
        assert idx == 231 and cat == AQICategory.POOR

    def test_half_value_in_interpolation_co(self):
        """CO = 1.51: [1,2]→[50,100]; slope=50; raw = 50*0.51+50 = 75.5 → 76.
        With banker's rounding this would be 76 (even) — same in this case.
        """
        idx, cat, _, _ = calculate_sub_index(PollutantType.CO, 1.51, "mg/m³", hours_recorded=24.0)
        assert idx == 76 and cat == AQICategory.SATISFACTORY

    def test_half_value_distinguishing_case(self):
        """CO = 1.01: [1,2]→[50,100]; slope=50; raw = 50*0.01+50 = 50.5 → 51.
        With banker's rounding: round(50.5) = 50 (even). Our result: 51.
        """
        idx, cat, _, _ = calculate_sub_index(PollutantType.CO, 1.01, "mg/m³", hours_recorded=24.0)
        assert idx == 51 and cat == AQICategory.SATISFACTORY


# =====================================================================
# 7. BOUNDARY & CONTINUITY TESTS
# =====================================================================

class TestBoundariesAndContinuity:
    """Verify continuous piecewise linear function at breakpoint transitions."""

    def test_zero_concentration(self):
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM25, 0.0, "µg/m³")
        assert idx == 0 and cat == AQICategory.GOOD

    def test_continuity_at_pm25_30(self):
        """At C=30 (Good/Satisfactory boundary), sub_index = 50 from both sides."""
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM25, 30.0, "µg/m³")
        assert idx == 50

    def test_continuity_at_pm10_250(self):
        """At C=250 (Moderate/Poor boundary), sub_index = 200 from both sides."""
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM10, 250.0, "µg/m³")
        assert idx == 200

    def test_severe_boundary_exact(self):
        """At exactly the Severe threshold, falls in Very Poor with sub_index 400."""
        idx, cat, _, _ = calculate_sub_index(PollutantType.PM25, 250.0, "µg/m³")
        assert idx == 400 and cat == AQICategory.VERY_POOR

    def test_category_classification_boundaries(self):
        assert get_category_for_index(0) == AQICategory.GOOD
        assert get_category_for_index(50) == AQICategory.GOOD
        assert get_category_for_index(51) == AQICategory.SATISFACTORY
        assert get_category_for_index(100) == AQICategory.SATISFACTORY
        assert get_category_for_index(101) == AQICategory.MODERATE
        assert get_category_for_index(200) == AQICategory.MODERATE
        assert get_category_for_index(201) == AQICategory.POOR
        assert get_category_for_index(300) == AQICategory.POOR
        assert get_category_for_index(301) == AQICategory.VERY_POOR
        assert get_category_for_index(400) == AQICategory.VERY_POOR
        assert get_category_for_index(401) == AQICategory.SEVERE
        assert get_category_for_index(500) == AQICategory.SEVERE
        assert get_category_for_index(-1) == AQICategory.UNKNOWN

    def test_breakpoint_continuity_all_pollutants(self):
        """Verify I_HI(k) == I_LO(k+1) for all adjacent breakpoint pairs."""
        for pollutant, breakpoints in CPCB_BREAKPOINTS.items():
            for i in range(len(breakpoints) - 1):
                current = breakpoints[i]
                next_bp = breakpoints[i + 1]
                assert current.i_hi == next_bp.i_lo, (
                    f"{pollutant.value}: discontinuity between {current.category.value} "
                    f"(i_hi={current.i_hi}) and {next_bp.category.value} (i_lo={next_bp.i_lo})"
                )
                if current.b_hi is not None:
                    assert current.b_hi == next_bp.b_lo, (
                        f"{pollutant.value}: concentration gap between "
                        f"{current.category.value} (b_hi={current.b_hi}) and "
                        f"{next_bp.category.value} (b_lo={next_bp.b_lo})"
                    )


# =====================================================================
# 8. INPUT VALIDATION TESTS
# =====================================================================

class TestInputValidation:
    def test_negative_rejection(self):
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, -12.5, "µg/m³")
        assert idx is None and cat == AQICategory.UNKNOWN
        assert "negative values are physically impossible" in err

    def test_nan_rejection(self):
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, float("nan"), "µg/m³")
        assert idx is None and cat == AQICategory.UNKNOWN
        assert "value must be a real finite number" in err

    def test_inf_rejection(self):
        idx, cat, err, _ = calculate_sub_index(PollutantType.PM25, float("inf"), "µg/m³")
        assert idx is None and cat == AQICategory.UNKNOWN
        assert "value must be a real finite number" in err

    def test_co_wrong_unit(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.CO, 2.5, "µg/m³", hours_recorded=24.0)
        assert idx is None
        assert "Incorrect unit for CO: expected 'mg/m³'" in err

    def test_pm25_wrong_unit(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.PM25, 45.0, "ppm")
        assert idx is None
        assert "Incorrect unit for PM2.5: expected 'µg/m³'" in err

    def test_alternative_unit_formats(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.PM25, 30.0, "ug/m3")
        assert idx == 50 and err is None

        idx_co, _, err_co, _ = calculate_sub_index(PollutantType.CO, 1.0, "mg/m3", hours_recorded=24.0)
        assert idx_co == 50 and err_co is None

    def test_min_hours_24hr_pollutant(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.PM25, 45.0, "µg/m³", hours_recorded=15.5)
        assert idx is None
        assert "minimum 16.0 hours required" in err

    def test_min_hours_24hr_accepted(self):
        idx, _, err, _ = calculate_sub_index(PollutantType.PM25, 45.0, "µg/m³", hours_recorded=16.0)
        assert idx == 75 and err is None

    def test_min_hours_uniform_16(self):
        """All pollutants require 16 hours minimum."""
        for pollutant, min_hrs in POLLUTANT_MIN_HOURS.items():
            assert min_hrs == 16.0, (
                f"{pollutant.value}: expected min_hours=16.0, got {min_hrs}"
            )


# =====================================================================
# 9. OVERALL AQI RULES
# =====================================================================

class TestOverallAQI:
    def test_minimum_three_pollutants_rule(self):
        sub_indices = {
            PollutantType.PM25: SubIndexValue(150, 150, True),
            PollutantType.PM10: SubIndexValue(120, 120, True),
        }
        result = calculate_overall_aqi(sub_indices)
        assert result["overall_aqi"] is None
        assert result["category"] == AQICategory.UNKNOWN
        assert result["dominant_pollutant"] is None
        assert result["is_eligible"] is False
        assert "at least 3 pollutants" in result["reason"]

    def test_mandatory_particulate_rule(self):
        sub_indices = {
            PollutantType.NO2: SubIndexValue(80, 80, True),
            PollutantType.SO2: SubIndexValue(45, 45, True),
            PollutantType.CO: SubIndexValue(60, 60, True),
        }
        result = calculate_overall_aqi(sub_indices)
        assert result["overall_aqi"] is None
        assert result["is_eligible"] is False
        assert "Mandatory particulate requirement not met" in result["reason"]

    def test_successful_exact_overall_aqi(self):
        sub_indices = {
            PollutantType.PM25: SubIndexValue(320, 320, True),
            PollutantType.PM10: SubIndexValue(140, 140, True),
            PollutantType.NO2: SubIndexValue(65, 65, True),
            PollutantType.SO2: SubIndexValue(30, 30, True),
        }
        result = calculate_overall_aqi(sub_indices)
        assert result["overall_aqi"] == 320
        assert result["overall_aqi_lower_bound"] == 320
        assert result["overall_aqi_upper_bound"] == 320
        assert result["is_exact"] is True
        assert result["category"] == AQICategory.VERY_POOR
        assert result["dominant_pollutant"] == PollutantType.PM25
        assert result["is_eligible"] is True
        assert "Dominant: PM2.5" in result["reason"]

    def test_overall_with_severe_dominant(self):
        """When dominant is Severe (range), overall_aqi is None with range bounds."""
        sub_indices = {
            PollutantType.PM25: SubIndexValue(401, 500, False),  # Severe
            PollutantType.PM10: SubIndexValue(200, 200, True),
            PollutantType.NO2: SubIndexValue(80, 80, True),
        }
        result = calculate_overall_aqi(sub_indices)
        assert result["overall_aqi"] is None
        assert result["overall_aqi_lower_bound"] == 401
        assert result["overall_aqi_upper_bound"] == 500
        assert result["is_exact"] is False
        assert result["category"] == AQICategory.SEVERE
        assert result["dominant_pollutant"] == PollutantType.PM25
        assert result["is_eligible"] is True


# =====================================================================
# 10. ORCHESTRATION (compute_station_cpcb_aqi)
# =====================================================================

class TestOrchestration:
    def test_valid_station(self):
        measurements = [
            {"pollutant": "PM2.5", "value": 130.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 180.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 45.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "CO", "value": 1.2, "unit": "mg/m³", "hours_recorded": 24.0},
            {"pollutant": "SO2", "value": 30.0, "unit": "µg/m³", "hours_recorded": 10.0},
        ]
        res = compute_station_cpcb_aqi(measurements)
        assert res["status"] == "CALCULATED"
        assert res["eligible_for_overall_aqi"] is True
        assert res["has_mandatory_pm"] is True
        assert res["is_exact"] is True
        assert res["dominant_pollutant"] == "PM2.5"
        assert res["overall_aqi"] is not None
        assert res["overall_aqi"] > 300

        assert res["sub_indices"]["PM2.5"]["is_valid"] is True
        assert res["sub_indices"]["SO2"]["is_valid"] is False
        assert "Insufficient monitoring duration" in res["sub_indices"]["SO2"]["validation_error"]

    def test_severe_station_with_ranges(self):
        measurements = [
            {"pollutant": "PM2.5", "value": 300.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 500.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 45.0, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
        res = compute_station_cpcb_aqi(measurements)
        assert res["status"] == "CALCULATED"
        assert res["overall_aqi"] is None
        assert res["overall_aqi_lower_bound"] == 401
        assert res["overall_aqi_upper_bound"] == 500
        assert res["is_exact"] is False
        assert res["category"] == "Severe"
        assert res["sub_indices"]["PM2.5"]["sub_index"] is None
        assert res["sub_indices"]["PM2.5"]["sub_index_lower_bound"] == 401
        assert res["sub_indices"]["PM2.5"]["is_exact"] is False
        assert res["sub_indices"]["PM2.5"]["is_valid"] is True
        assert res["sub_indices"]["PM2.5"]["note"] is not None

    def test_all_eight_pollutants(self):
        measurements = [
            {"pollutant": "PM2.5", "value": 85.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 150.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 55.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "SO2", "value": 35.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "CO", "value": 1.5, "unit": "mg/m³", "hours_recorded": 24.0},
            {"pollutant": "O3", "value": 65.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NH3", "value": 250.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "Pb", "value": 0.8, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
        res = compute_station_cpcb_aqi(measurements)
        assert res["status"] == "CALCULATED"
        assert res["valid_pollutants_count"] == 8
        assert res["is_exact"] is True
        for p in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"]:
            assert res["sub_indices"][p]["is_valid"] is True
            assert res["sub_indices"][p]["is_exact"] is True

    def test_empty_measurements(self):
        res = compute_station_cpcb_aqi([])
        assert res["status"] == "UNAVAILABLE"
        assert res["eligible_for_overall_aqi"] is False
        assert res["overall_aqi"] is None
        assert res["is_exact"] is False

    def test_unrecognized_pollutant(self):
        measurements = [
            {"pollutant": "Benzene", "value": 5.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM2.5", "value": 45.0, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
        res = compute_station_cpcb_aqi(measurements)
        assert res["status"] == "UNAVAILABLE"
        assert "Benzene" in res["sub_indices"]
        assert res["sub_indices"]["Benzene"]["is_valid"] is False
        assert "Unrecognized CPCB criteria pollutant" in res["sub_indices"]["Benzene"]["validation_error"]


# =====================================================================
# 11. FASTAPI ENDPOINT INTEGRATION TESTS
# =====================================================================

@pytest.mark.anyio
async def test_api_calculate_endpoint():
    payload = {
        "measurements": [
            {"pollutant": "PM2.5", "value": 75.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 120.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 35.0, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/aqi/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CALCULATED"
        assert data["eligible_for_overall_aqi"] is True
        assert data["is_exact"] is True
        assert data["overall_aqi"] is not None
        assert data["overall_aqi"] == data["overall_aqi_lower_bound"]
        assert data["overall_aqi"] == data["overall_aqi_upper_bound"]
        assert data["dominant_pollutant"] in ["PM2.5", "PM10"]
        assert "sub_indices" in data
        pm25_sub = data["sub_indices"]["PM2.5"]
        assert pm25_sub["sub_index"] is not None
        assert pm25_sub["is_exact"] is True


@pytest.mark.anyio
async def test_api_severe_includes_range():
    """API response for Severe should include range representation."""
    payload = {
        "measurements": [
            {"pollutant": "PM2.5", "value": 300.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "PM10", "value": 200.0, "unit": "µg/m³", "hours_recorded": 24.0},
            {"pollutant": "NO2", "value": 50.0, "unit": "µg/m³", "hours_recorded": 24.0},
        ]
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/aqi/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CALCULATED"
        # Overall is Severe range
        assert data["overall_aqi"] is None
        assert data["overall_aqi_lower_bound"] == 401
        assert data["overall_aqi_upper_bound"] == 500
        assert data["is_exact"] is False
        assert data["category"] == "Severe"
        # PM2.5 sub-index is Severe range
        pm25_sub = data["sub_indices"]["PM2.5"]
        assert pm25_sub["sub_index"] is None
        assert pm25_sub["sub_index_lower_bound"] == 401
        assert pm25_sub["sub_index_upper_bound"] == 500
        assert pm25_sub["is_exact"] is False
        assert pm25_sub["note"] is not None
        assert "Severe" in pm25_sub["note"]
