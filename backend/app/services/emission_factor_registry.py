"""Audited static Emission Factor Registry for SmogShield AI.

Maintains exactly 9 verified emission factor entries:
- 8 road transport factors from India GHG Program (2015 stakeholder consultation paper)
  with strict less-than (<) engine displacement boundaries (< 125 cc, < 1400 cc)
  and separate base vs uplifted entries.
- 1 electricity grid factor from Central Electricity Authority (CEA) CO2 Baseline Database V22.0
  (0.675 kg CO2/kWh, All-India generation-weighted average for FY 2025-26) with explicit
  FY 2026-27 prior-year estimate disclosures.
"""

from typing import Dict, List, Optional
from app.schemas.transport import EmissionFactorEntry, FactorVerificationStatus


# Exactly 9 Audited Emission Factor Entries
EMISSION_FACTORS: Dict[str, EmissionFactorEntry] = {
    "PETROL_MOTORCYCLE_BASE": EmissionFactorEntry(
        factor_id="PETROL_MOTORCYCLE_BASE",
        mode="petrol_motorcycle",
        fuel_type="petrol",
        engine_capacity_boundary="< 125 cc",
        base_value=0.0290,
        uplift_pct=None,
        default_value=0.0290,
        unit="kg CO2/veh-km",
        is_default_for_calc=False,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="p. 20-24",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Applies strictly to engine displacement < 125 cc. Test-cycle baseline without real-world uplift. Excludes motorcycles >= 125 cc.",
        methodology_notes="Stakeholder consultation paper. Historical provisional factor for reference only; not used as active commute default."
    ),
    "PETROL_MOTORCYCLE_UPLIFT": EmissionFactorEntry(
        factor_id="PETROL_MOTORCYCLE_UPLIFT",
        mode="petrol_motorcycle",
        fuel_type="petrol",
        engine_capacity_boundary="< 125 cc",
        base_value=0.0290,
        uplift_pct=10.0,
        default_value=0.0319,
        unit="kg CO2/veh-km",
        is_default_for_calc=True,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="p. 20-24",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Applies strictly to engine displacement < 125 cc. Incorporates 10% real-world uplift. Excludes motorcycles >= 125 cc.",
        methodology_notes="Active default factor for real-world commuter calculations. Historical provisional status must be disclosed to users."
    ),
    "PETROL_CAR_HATCHBACK_BASE": EmissionFactorEntry(
        factor_id="PETROL_CAR_HATCHBACK_BASE",
        mode="petrol_car",
        fuel_type="petrol",
        engine_capacity_boundary="< 1400 cc",
        base_value=0.130,
        uplift_pct=None,
        default_value=0.130,
        unit="kg CO2/veh-km",
        is_default_for_calc=False,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="p. 28-30",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Applies strictly to petrol hatchback passenger cars with engine displacement < 1400 cc. Excludes cars >= 1400 cc, sedans, and SUVs.",
        methodology_notes="Test-cycle baseline without real-world uplift. Retained for reference; not used as active commute default."
    ),
    "PETROL_CAR_HATCHBACK_UPLIFT": EmissionFactorEntry(
        factor_id="PETROL_CAR_HATCHBACK_UPLIFT",
        mode="petrol_car",
        fuel_type="petrol",
        engine_capacity_boundary="< 1400 cc",
        base_value=0.130,
        uplift_pct=8.0,
        default_value=0.140,
        unit="kg CO2/veh-km",
        is_default_for_calc=True,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="p. 28-30",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Applies strictly to petrol hatchback passenger cars with engine displacement < 1400 cc. Incorporates 8% real-world uplift. Excludes cars >= 1400 cc.",
        methodology_notes="Active default factor for petrol hatchback commute estimates. Per-passenger emissions require dividing by total vehicle occupancy."
    ),
    "DIESEL_CAR_HATCHBACK_BASE": EmissionFactorEntry(
        factor_id="DIESEL_CAR_HATCHBACK_BASE",
        mode="diesel_car",
        fuel_type="diesel",
        engine_capacity_boundary="< 1400 cc",
        base_value=0.117,
        uplift_pct=None,
        default_value=0.117,
        unit="kg CO2/veh-km",
        is_default_for_calc=False,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="p. 28-32",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Applies strictly to diesel hatchback passenger cars with engine displacement < 1400 cc. Excludes diesel cars >= 1400 cc.",
        methodology_notes="Test-cycle baseline without real-world uplift. Retained for reference; not used as active commute default."
    ),
    "DIESEL_CAR_HATCHBACK_UPLIFT": EmissionFactorEntry(
        factor_id="DIESEL_CAR_HATCHBACK_UPLIFT",
        mode="diesel_car",
        fuel_type="diesel",
        engine_capacity_boundary="< 1400 cc",
        base_value=0.117,
        uplift_pct=8.0,
        default_value=0.126,
        unit="kg CO2/veh-km",
        is_default_for_calc=True,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="p. 28-32",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Applies strictly to diesel hatchback passenger cars with engine displacement < 1400 cc. Incorporates 8% real-world uplift. Excludes diesel cars >= 1400 cc.",
        methodology_notes="Active default factor for diesel hatchback commute estimates. Per-passenger emissions require dividing by total vehicle occupancy."
    ),
    "CNG_AUTO_RICKSHAW": EmissionFactorEntry(
        factor_id="CNG_AUTO_RICKSHAW",
        mode="cng_auto",
        fuel_type="cng",
        engine_capacity_boundary=None,
        base_value=0.10768,
        uplift_pct=None,
        default_value=0.10768,
        unit="kg CO2/veh-km",
        is_default_for_calc=True,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="§4.2 summary tables",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Three-wheeler passenger auto-rickshaws running on compressed natural gas (CNG). Maximum occupancy is 3 passengers. Factor is per-vehicle-km.",
        methodology_notes="Per-passenger emissions require dividing by total vehicle occupancy (driver + passengers, max 3)."
    ),
    "INTRACITY_BUS_SRTU": EmissionFactorEntry(
        factor_id="INTRACITY_BUS_SRTU",
        mode="intracity_bus",
        fuel_type="diesel",
        engine_capacity_boundary=None,
        base_value=0.015161,
        uplift_pct=None,
        default_value=0.015161,
        unit="kg CO2/pax-km",
        is_default_for_calc=True,
        verification_status=FactorVerificationStatus.HISTORICAL_PROVISIONAL,
        source_name="India GHG Program (WRI India / TERI / CII)",
        document_title="India Specific Road Transport Emission Factors",
        publication_year=2015,
        publication_date="2015",
        applicable_fiscal_year="2014-15",
        source_page="§4.5 intracity bus tables",
        geography="India",
        calculation_scope="Tailpipe CO2",
        limitations="Applies ONLY to standard intracity State Road Transport Undertaking (SRTU) bus operations. Strictly does NOT apply to Bus Rapid Transit Systems (BRTS) or intercity bus routes.",
        methodology_notes="Factor is ALREADY denominated in passenger-kilometers (pax-km) based on average SRTU fleet loadings. NEVER divide this factor by occupancy."
    ),
    "INDIA_GRID_WEIGHTED_AVG": EmissionFactorEntry(
        factor_id="INDIA_GRID_WEIGHTED_AVG",
        mode="electricity_grid",
        fuel_type="electric",
        engine_capacity_boundary=None,
        base_value=0.675,
        uplift_pct=None,
        default_value=0.675,
        unit="kg CO2/kWh",
        is_default_for_calc=True,
        verification_status=FactorVerificationStatus.VERIFIED_CURRENT,
        source_name="Central Electricity Authority (CEA), Ministry of Power, Government of India",
        document_title="CO2 Baseline Database for the Indian Power Sector, Version 22.0",
        publication_year=2026,
        publication_date="August 2026",
        applicable_fiscal_year="FY 2025-26",
        source_page="Section 4, Table 1 (All-India Weighted Average)",
        geography="All-India (National Grid)",
        calculation_scope="Indirect Generation CO2 (Scope 2 Location-Based)",
        limitations="All-India generation-weighted average gross electricity factor. Excludes transmission/distribution losses. Not state-specific. Not a marginal avoided-emissions factor.",
        methodology_notes="Latest official CEA release covering FY 2025-26. Used in SmogShield AI as a prior-year estimate for FY 2026-27 calculations because official FY 2026-27 figures are not yet published."
    ),
}


class EmissionFactorRegistry:
    """Registry access service providing audited lookup and strict boundary validation."""

    @classmethod
    def get_all_factors(cls) -> List[EmissionFactorEntry]:
        """Return all 9 audited factors."""
        return list(EMISSION_FACTORS.values())

    @classmethod
    def get_factor(cls, factor_id: str) -> Optional[EmissionFactorEntry]:
        """Lookup by unique factor ID."""
        return EMISSION_FACTORS.get(factor_id)

    @classmethod
    def resolve_road_factor(
        cls,
        mode: str,
        fuel_type: Optional[str] = None,
        engine_capacity_cc: Optional[int] = None,
    ) -> Optional[EmissionFactorEntry]:
        """Resolve active default factor with strict < capacity boundaries.
        
        Returns None (UNAVAILABLE) if engine capacity does not satisfy strict less-than criteria.
        """
        if mode == "petrol_motorcycle":
            if engine_capacity_cc is None or engine_capacity_cc < 125:
                return EMISSION_FACTORS["PETROL_MOTORCYCLE_UPLIFT"]
            return None  # >= 125cc is UNAVAILABLE

        if mode == "petrol_car":
            if engine_capacity_cc is None or engine_capacity_cc < 1400:
                return EMISSION_FACTORS["PETROL_CAR_HATCHBACK_UPLIFT"]
            return None  # >= 1400cc is UNAVAILABLE

        if mode == "diesel_car":
            if engine_capacity_cc is None or engine_capacity_cc < 1400:
                return EMISSION_FACTORS["DIESEL_CAR_HATCHBACK_UPLIFT"]
            return None  # >= 1400cc is UNAVAILABLE

        if mode == "cng_auto":
            return EMISSION_FACTORS["CNG_AUTO_RICKSHAW"]

        if mode == "intracity_bus":
            return EMISSION_FACTORS["INTRACITY_BUS_SRTU"]

        return None

    @classmethod
    def get_grid_factor(cls) -> EmissionFactorEntry:
        """Return the CEA national grid emission factor."""
        return EMISSION_FACTORS["INDIA_GRID_WEIGHTED_AVG"]


emission_factor_registry = EmissionFactorRegistry()
