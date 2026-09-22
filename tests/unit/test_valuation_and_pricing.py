"""Unit tests for Deterministic Valuation Engine, Dynamic Pricing Engine, and Confidence Scoring."""

import pytest
from src.core.comparable_engine import CMAEngine
from src.core.enums import ConfidenceLevel, DataOrigin, PropertyCondition, PropertyType
from src.core.lease_engine import LeaseAnalysisEngine
from src.core.models import (
    LEGAL_DISCLAIMER_TEXT,
    CMAAnalysis,
    ComparableProperty,
    MarketRecord,
    PropertyProfile,
    ProvenanceMetadata,
)
from src.core.pricing_engine import DeterministicPricingEngine
from src.core.scoring import ConfidenceScoringEngine
from src.core.valuation_engine import DeterministicValuationEngine
from src.data.providers.synthetic_provider import (
    SyntheticMarketDataProvider,
    SyntheticRentRollProvider,
)


@pytest.fixture
def market_provider():
    return SyntheticMarketDataProvider()


@pytest.fixture
def rentroll_provider():
    return SyntheticRentRollProvider()


@pytest.fixture
def sample_subject():
    return PropertyProfile(
        property_id="PROP-ATX-001",
        address="1204 Colorado St",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        sqft=1150.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2019,
        condition=PropertyCondition.EXCELLENT,
        amenities=["Pool", "Gym", "Concierge", "Balcony"],
        parking_spaces=1,
        current_rent=3000.0,
    )


def test_deterministic_valuation_with_cma_and_income(sample_subject, market_provider, rentroll_provider):
    """Verify valuation calculation combining CMA, momentum trend, and income capitalization."""
    records = market_provider.get_sales_comps("Austin", "78701", limit=6)
    cma_engine = CMAEngine()
    comps, cma = cma_engine.generate_cma(sample_subject, records)

    trends = market_provider.get_market_trends("Austin-Downtown")
    units = rentroll_provider.get_rent_roll("PROP-ATX-001")
    rent_summary = LeaseAnalysisEngine.analyze_rent_roll("PROP-ATX-001", units)

    val_engine = DeterministicValuationEngine()
    result = val_engine.calculate_valuation(
        subject=sample_subject,
        comparables=comps,
        cma_analysis=cma,
        market_conditions=trends,
        rent_roll_summary=rent_summary,
    )

    assert result.estimated_value > 0
    assert result.valuation_range_low <= result.estimated_value <= result.valuation_range_high
    assert result.valuation_psf == round(result.estimated_value / sample_subject.sqft, 2)
    assert result.breakdown.cma_sales_component > 0
    assert result.breakdown.income_capitalization_component is not None
    assert result.breakdown.income_capitalization_component > 0
    assert result.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
    assert result.legal_disclaimer == LEGAL_DISCLAIMER_TEXT
    assert len(result.key_drivers) >= 2


def test_valuation_missing_data_fallbacks(sample_subject):
    """Verify valuation handles zero comps and missing market conditions without crashing."""
    val_engine = DeterministicValuationEngine()
    empty_cma = CMAAnalysis(
        subject_property_id=sample_subject.property_id,
        comparables=[],
        unadjusted_median_price=0.0,
        unadjusted_mean_price=0.0,
        adjusted_median_price=0.0,
        adjusted_mean_price=0.0,
        adjusted_price_low=0.0,
        adjusted_price_high=0.0,
        adjusted_psf_mean=0.0,
        outlier_count=0,
        methodology_notes="No comps",
    )

    result = val_engine.calculate_valuation(
        subject=sample_subject,
        comparables=[],
        cma_analysis=empty_cma,
        market_conditions=None,
        rent_roll_summary=None,
    )

    assert result.estimated_value > 0
    assert result.confidence_level == ConfidenceLevel.LOW
    assert any("data quality haircut" in lim.lower() for lim in result.limitations)
    assert any("defaulted to submarket average" in lim.lower() for lim in result.limitations)


def test_dynamic_rental_pricing_floor_midpoint_ceiling(sample_subject, market_provider, rentroll_provider):
    """Verify rental pricing produces consistent floor <= midpoint <= ceiling and rent gap."""
    rentals = market_provider.get_rental_comps("Austin", "78701", limit=6)
    trends = market_provider.get_market_trends("Austin-Downtown")
    units = rentroll_provider.get_rent_roll("PROP-ATX-001")
    rent_summary = LeaseAnalysisEngine.analyze_rent_roll("PROP-ATX-001", units)

    pricing_engine = DeterministicPricingEngine()
    result = pricing_engine.calculate_rental_pricing(
        subject=sample_subject,
        rental_records=rentals,
        market_conditions=trends,
        rent_roll_summary=rent_summary,
    )

    assert result.recommended_rent_range_low <= result.recommended_midpoint <= result.recommended_rent_range_high
    assert result.estimated_market_rent == result.recommended_midpoint
    assert result.breakdown.base_market_comp_rent > 0
    assert result.current_in_place_rent is not None
    assert result.rent_gap_amount is not None
    assert result.rent_gap_percentage is not None
    assert result.disclaimer == LEGAL_DISCLAIMER_TEXT
    assert len(result.pricing_drivers) >= 2


def test_dynamic_pricing_missing_rentals_fallback(sample_subject):
    """Verify dynamic pricing gracefully handles missing rental records."""
    pricing_engine = DeterministicPricingEngine()
    result = pricing_engine.calculate_rental_pricing(
        subject=sample_subject,
        rental_records=[],
        market_conditions=None,
        rent_roll_summary=None,
    )
    assert result.recommended_midpoint > 0
    assert result.recommended_rent_range_low < result.recommended_midpoint < result.recommended_rent_range_high


def test_confidence_scoring_tiers():
    """Verify confidence scoring logic correctly separates HIGH, MEDIUM, and LOW tiers."""
    prov = ProvenanceMetadata(source="Test", origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)

    # 1. High confidence scenario (5 close, highly similar comps, low variance)
    high_comps = []
    for i in range(5):
        rec = MarketRecord(
            record_id=f"R{i}", address=f"Addr {i}", city="Austin", state="TX", zip_code="78701",
            property_type=PropertyType.CONDO, transaction_date="2025-10-01", sale_price=580000.0 + i * 2000.0,
            sqft=1150.0, bedrooms=2, bathrooms=2.0, year_built=2019, distance_miles=0.2, provenance=prov,
        )
        high_comps.append(ComparableProperty(
            record=rec, similarity_score=0.92, adjustments=[], total_net_adjustment=0.0,
            adjusted_price=580000.0 + i * 2000.0, adjusted_price_psf=505.0, selection_rationale="test", is_outlier=False,
        ))

    level_high, score_high, _ = ConfidenceScoringEngine.calculate_confidence(
        comparables=high_comps,
        has_complete_specs=True,
    )
    assert level_high in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
    assert score_high >= 60.0

    # 2. Low confidence scenario (0 comps)
    level_low, score_low, _ = ConfidenceScoringEngine.calculate_confidence(
        comparables=[],
        market_conditions=None,
        rent_roll_summary=None,
        has_complete_specs=False,
    )
    assert level_low == ConfidenceLevel.LOW
    assert score_low < 50.0


def test_deterministic_reproducibility_valuation(sample_subject, market_provider):
    """Verify repeated valuation calculations produce identical outputs down to the dollar."""
    records = market_provider.get_sales_comps("Austin", "78701", limit=5)
    cma_engine = CMAEngine()
    comps, cma = cma_engine.generate_cma(sample_subject, records)
    trends = market_provider.get_market_trends("Austin-Downtown")

    val_engine = DeterministicValuationEngine()
    res1 = val_engine.calculate_valuation(sample_subject, comps, cma, trends)
    res2 = val_engine.calculate_valuation(sample_subject, comps, cma, trends)

    assert res1.estimated_value == res2.estimated_value
    assert res1.valuation_range_low == res2.valuation_range_low
    assert res1.valuation_range_high == res2.valuation_range_high
    assert res1.confidence_score == res2.confidence_score
    assert res1.breakdown.cma_sales_component == res2.breakdown.cma_sales_component
