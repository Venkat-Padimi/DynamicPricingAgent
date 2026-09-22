"""Unit tests for Property Intake, Multi-Attribute Similarity, Appraisal Adjustments, and CMA Engine."""

import pytest
from src.core.comparable_engine import (
    AdjustmentEngine,
    CMAEngine,
    OutlierDetector,
    SimilarityCalculator,
)
from src.core.enums import DataOrigin, PropertyCondition, PropertyType
from src.core.intake_engine import PropertyIntakeEngine
from src.core.models import ComparableProperty, MarketRecord, PropertyProfile, ProvenanceMetadata
from src.data.providers.synthetic_provider import SyntheticMarketDataProvider


@pytest.fixture
def sample_subject():
    return PropertyProfile(
        property_id="PROP-SUBJ-001",
        address="1200 Colorado St",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        sqft=1150.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2019,
        condition=PropertyCondition.EXCELLENT,
        amenities=["Pool", "Gym", "Concierge"],
        parking_spaces=1,
    )


@pytest.fixture
def market_provider():
    return SyntheticMarketDataProvider()


def test_property_intake_normalization():
    """Verify property intake parser normalizes types, conditions, and validates required fields."""
    raw = {
        "address": "500 Congress Ave",
        "city": "Austin",
        "state": "tx",
        "zip_code": "78701",
        "property_type": "condominium",
        "sqft": "1200",
        "bedrooms": 2,
        "bathrooms": 2.0,
        "year_built": 2020,
        "condition": "luxury",
        "amenities": ["Pool", "Gym"],
    }
    profile = PropertyIntakeEngine.parse_and_validate(raw)
    assert profile.property_type == PropertyType.CONDO
    assert profile.condition == PropertyCondition.LUXURY_RENOVATED
    assert profile.sqft == 1200.0
    assert profile.state == "TX"
    assert profile.data_origin == DataOrigin.USER_PROVIDED_DATA

    # Required field validation
    with pytest.raises(ValueError, match="'address' is required"):
        PropertyIntakeEngine.parse_and_validate({"city": "Austin", "zip_code": "78701", "sqft": 1000})

    with pytest.raises(ValueError, match="invalid or missing 'sqft'"):
        PropertyIntakeEngine.parse_and_validate({"address": "123 Main", "city": "Austin", "zip_code": "78701", "sqft": -10})


def test_similarity_calculator_identical_vs_dissimilar(sample_subject):
    """Verify similarity scoring is high for near-identical properties and low for divergent ones."""
    calc = SimilarityCalculator()

    prov = ProvenanceMetadata(
        source="Synthetic Demo",
        origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
    )

    near_identical = MarketRecord(
        record_id="REC-SIM-1",
        address="1204 Colorado St",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        transaction_date="2025-11-01",
        sale_price=580000.0,
        sqft=1150.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2019,
        condition=PropertyCondition.EXCELLENT,
        distance_miles=0.1,
        amenities=["Pool", "Gym", "Concierge"],
        provenance=prov,
    )

    dissimilar = MarketRecord(
        record_id="REC-SIM-2",
        address="3500 Rural Way",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.SINGLE_FAMILY,
        transaction_date="2024-01-01",
        sale_price=1200000.0,
        sqft=2800.0,
        bedrooms=4,
        bathrooms=3.5,
        year_built=1995,
        condition=PropertyCondition.FAIR,
        distance_miles=2.8,
        amenities=["Barn"],
        provenance=prov,
    )

    sim_high = calc.calculate_similarity(sample_subject, near_identical)
    sim_low = calc.calculate_similarity(sample_subject, dissimilar)

    assert sim_high >= 0.90
    assert sim_low <= 0.50
    assert sim_high > sim_low


def test_similarity_custom_weights(sample_subject):
    """Verify configurable similarity weights adjust ranking behavior."""
    # Weight distance heavily
    calc_dist = SimilarityCalculator(weights={"distance": 0.8, "sqft": 0.1, "beds_baths": 0.05, "age": 0.05, "condition": 0.0, "amenities": 0.0})
    # Weight sqft heavily
    calc_sqft = SimilarityCalculator(weights={"distance": 0.0, "sqft": 0.8, "beds_baths": 0.1, "age": 0.05, "condition": 0.05, "amenities": 0.0})

    prov = ProvenanceMetadata(source="Demo", origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    comp_close_diff_size = MarketRecord(
        record_id="C1", address="A", city="Austin", state="TX", zip_code="78701",
        property_type=PropertyType.CONDO, transaction_date="2025-01-01",
        sale_price=500000.0, sqft=1600.0, bedrooms=2, bathrooms=2.0, year_built=2019,
        distance_miles=0.1, provenance=prov,
    )
    score_dist = calc_dist.calculate_similarity(sample_subject, comp_close_diff_size)
    score_sqft = calc_sqft.calculate_similarity(sample_subject, comp_close_diff_size)
    assert score_dist > score_sqft


def test_appraisal_adjustments_rule(sample_subject):
    """Verify appraisal rule: Adjust comparable to the subject.

    If subject has superior attributes, comp is adjusted UP (+).
    If comp has superior attributes, comp is adjusted DOWN (-).
    """
    prov = ProvenanceMetadata(source="Demo", origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    # Comp is smaller (1050 sqft vs 1150 subject), older (2015 vs 2019), condition Good vs Excellent
    comp = MarketRecord(
        record_id="COMP-ADJ-1",
        address="1110 San Antonio St",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        transaction_date="2025-10-01",
        sale_price=520000.0,
        sqft=1050.0,  # 100 sqft smaller -> +$15,000 adj
        bedrooms=2,
        bathrooms=2.0,
        year_built=2015,  # 4 years older -> +$6,000 adj
        condition=PropertyCondition.GOOD,  # 1 rank lower -> +$12,000 adj
        distance_miles=0.3,
        amenities=["Pool", "Gym", "Concierge"],
        parking_spaces=1,
        provenance=prov,
    )

    adjustments, net_adj, adj_price = AdjustmentEngine.calculate_adjustments(sample_subject, comp)

    # Subject is superior in size, age, and condition -> net adjustment must be positive!
    assert net_adj > 0
    assert adj_price > comp.sale_price
    # Check specific line items
    adj_names = [a.feature_name for a in adjustments]
    assert "Square Footage" in adj_names
    assert "Year Built / Effective Age" in adj_names
    assert "Property Condition" in adj_names

    sqft_adj = next(a for a in adjustments if a.feature_name == "Square Footage")
    assert sqft_adj.adjustment_amount == 100.0 * AdjustmentEngine.SQFT_ADJUSTMENT_RATE  # Subject superior in size


def test_outlier_detection_iqr_and_zscore(sample_subject):
    """Verify statistical outlier detection tags extreme values."""
    prov = ProvenanceMetadata(source="Demo", origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    comps = []
    # 5 standard comps around $580k - $600k
    for i, p in enumerate([580000.0, 585000.0, 590000.0, 595000.0, 600000.0]):
        rec = MarketRecord(
            record_id=f"COMP-{i}", address=f"Addr {i}", city="Austin", state="TX", zip_code="78701",
            property_type=PropertyType.CONDO, transaction_date="2025-10-01",
            sale_price=p, sqft=1150.0, bedrooms=2, bathrooms=2.0, year_built=2019,
            distance_miles=0.2, provenance=prov,
        )
        comps.append(ComparableProperty(
            record=rec, similarity_score=0.9, adjustments=[], total_net_adjustment=0.0,
            adjusted_price=p, adjusted_price_psf=p / 1150.0, selection_rationale="test", is_outlier=False,
        ))

    # Add 1 extreme outlier ($1,500,000)
    rec_outlier = MarketRecord(
        record_id="COMP-OUTLIER", address="Penthouse", city="Austin", state="TX", zip_code="78701",
        property_type=PropertyType.CONDO, transaction_date="2025-10-01",
        sale_price=1500000.0, sqft=1150.0, bedrooms=2, bathrooms=2.0, year_built=2019,
        distance_miles=0.2, provenance=prov,
    )
    comps.append(ComparableProperty(
        record=rec_outlier, similarity_score=0.8, adjustments=[], total_net_adjustment=0.0,
        adjusted_price=1500000.0, adjusted_price_psf=1500000.0 / 1150.0, selection_rationale="test", is_outlier=False,
    ))

    tagged, count = OutlierDetector.detect_outliers(comps)
    assert count >= 1
    outlier_comp = next(c for c in tagged if c.record.record_id == "COMP-OUTLIER")
    assert outlier_comp.is_outlier is True


def test_cma_engine_end_to_end_with_synthetic_records(sample_subject, market_provider):
    """Verify CMAEngine produces structured CMAAnalysis with rationales, adjustments, and preserved provenance."""
    cma_engine = CMAEngine(min_similarity_threshold=0.50, max_comps_to_select=5)

    records = market_provider.get_sales_comps(city="Austin", zip_code="78701", limit=10)
    assert len(records) >= 5

    comparables, analysis = cma_engine.generate_cma(sample_subject, records)

    assert len(comparables) > 0
    assert analysis.adjusted_median_price > 0
    assert analysis.adjusted_mean_price > 0
    assert analysis.adjusted_price_low <= analysis.adjusted_median_price <= analysis.adjusted_price_high
    assert analysis.adjusted_psf_mean > 0

    # Verify provenance and rationales on each comparable
    for comp in comparables:
        assert comp.record.data_origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA
        assert "Synthetic demonstration data" in comp.record.provenance.notice
        assert "Selected with" in comp.selection_rationale
        assert len(comp.adjustments) > 0


def test_cma_engine_no_matching_comps_graceful_handling(sample_subject):
    """Verify graceful handling when no market records meet similarity threshold."""
    cma_engine = CMAEngine(min_similarity_threshold=0.999)  # Impossibly strict
    prov = ProvenanceMetadata(source="Demo", origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    dissimilar_rec = MarketRecord(
        record_id="DISSIMILAR", address="Farm Rd", city="Austin", state="TX", zip_code="78701",
        property_type=PropertyType.SINGLE_FAMILY, transaction_date="2020-01-01",
        sale_price=3000000.0, sqft=5000.0, bedrooms=6, bathrooms=6.0, year_built=1970,
        distance_miles=20.0, provenance=prov,
    )

    comps, analysis = cma_engine.generate_cma(sample_subject, [dissimilar_rec])
    assert comps == []
    assert analysis.adjusted_median_price == 0.0
    assert "No comparable properties met the minimum similarity criteria" in analysis.methodology_notes
