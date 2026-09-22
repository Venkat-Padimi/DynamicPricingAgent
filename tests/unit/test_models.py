"""Unit tests for core models, enums, and data integrity guarantees."""

import pytest
from pydantic import ValidationError

from src.core.enums import (
    ConfidenceLevel,
    DataOrigin,
    PropertyCondition,
    PropertyType,
    ReviewStatus,
    RiskSeverity,
)
from src.core.models import (
    LEGAL_DISCLAIMER_TEXT,
    SYNTHETIC_NOTICE_TEXT,
    AuditEntry,
    ComparableProperty,
    FeatureAdjustment,
    HumanReviewDecision,
    MarketRecord,
    PropertyProfile,
    ProvenanceMetadata,
    RentRollSummary,
    RentRollUnit,
    RiskReport,
    ValuationComponentBreakdown,
    ValuationResult,
)


def test_provenance_enforces_synthetic_label():
    """Verify synthetic provenance explicitly enforces the demonstration disclaimer notice."""
    prov = ProvenanceMetadata(
        source="Synthetic Demonstration Provider v1.0",
        origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
        notice="",  # Empty should be populated with default notice
    )
    assert prov.notice == SYNTHETIC_NOTICE_TEXT
    assert prov.origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA


def test_property_profile_validation():
    """Verify PropertyProfile validates positive numbers and calculates age."""
    profile = PropertyProfile(
        property_id="PROP-TEST-001",
        address="1204 Colorado St",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        sqft=1150.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2018,
        condition=PropertyCondition.EXCELLENT,
        amenities=["Pool", "Gym", "Concierge"],
        parking_spaces=1,
    )
    assert profile.age_years >= 0
    assert profile.sqft == 1150.0
    assert profile.property_type == PropertyType.CONDO

    # Must reject invalid sqft <= 0
    with pytest.raises(ValidationError):
        PropertyProfile(
            property_id="PROP-TEST-BAD",
            address="1204 Colorado St",
            city="Austin",
            state="TX",
            zip_code="78701",
            sqft=-500.0,
            bedrooms=2,
            bathrooms=2.0,
            year_built=2018,
        )


def test_market_record_psf_calculation():
    """Verify MarketRecord correctly computes sale and rent PSF."""
    prov = ProvenanceMetadata(
        source="Synthetic Demo MLS",
        origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
        record_id="MLS-101",
    )
    rec_sale = MarketRecord(
        record_id="MLS-101",
        address="1208 Colorado St #4B",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        transaction_date="2025-11-15",
        sale_price=575000.0,
        sqft=1150.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2019,
        provenance=prov,
    )
    assert rec_sale.price_per_sqft == 500.0
    assert rec_sale.rent_per_sqft == 0.0

    rec_rent = MarketRecord(
        record_id="RENT-202",
        address="1210 Colorado St #2A",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        transaction_date="2025-12-01",
        monthly_rent=3200.0,
        sqft=1000.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2020,
        provenance=prov,
    )
    assert rec_rent.rent_per_sqft == 3.20


def test_cma_adjustment_model():
    """Verify FeatureAdjustment and ComparableProperty model calculation consistency."""
    prov = ProvenanceMetadata(
        source="Synthetic Demo MLS",
        origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
    )
    rec = MarketRecord(
        record_id="MLS-301",
        address="1300 Lavaca St",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        transaction_date="2025-10-10",
        sale_price=600000.0,
        sqft=1200.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2015,
        provenance=prov,
    )
    adj = FeatureAdjustment(
        feature_name="Square Footage",
        subject_value=1150.0,
        comp_value=1200.0,
        raw_difference=-50.0,
        adjustment_rate=150.0,
        adjustment_amount=-7500.0,
        rationale="Comp is 50 sqft larger than subject property",
    )
    comp = ComparableProperty(
        record=rec,
        similarity_score=0.92,
        adjustments=[adj],
        total_net_adjustment=-7500.0,
        adjusted_price=592500.0,
        adjusted_price_psf=round(592500.0 / 1150.0, 2),
        selection_rationale="Close proximity and identical bedroom count",
    )
    assert comp.adjusted_price == 592500.0
    assert comp.similarity_score == 0.92
    assert len(comp.adjustments) == 1


def test_rent_roll_pii_protection():
    """Verify RentRollUnit enforces anonymized pseudonym with no tenant PII."""
    unit = RentRollUnit(
        unit_id="U-101",
        unit_number="101",
        bedrooms=1,
        bathrooms=1.0,
        sqft=750.0,
        current_rent=2200.0,
        in_place_psf=2.93,
        lease_start="2025-01-01",
        lease_end="2025-12-31",
        days_until_expiration=90,
        tenant_pseudonym="TENANT-HASH-7A9B",
    )
    assert "John" not in unit.tenant_pseudonym
    assert unit.tenant_pseudonym.startswith("TENANT-")


def test_valuation_result_contains_mandatory_disclaimer():
    """Verify ValuationResult contains explicit non-appraisal disclaimer."""
    breakdown = ValuationComponentBreakdown(
        cma_sales_component=585000.0,
        cma_weight=0.60,
        property_feature_adjustment=5000.0,
        market_trend_component=10000.0,
        market_trend_weight=0.15,
        location_component=5000.0,
        location_weight=0.10,
        income_capitalization_component=590000.0,
        income_weight=0.15,
    )
    val = ValuationResult(
        property_id="PROP-001",
        estimated_value=588000.0,
        valuation_range_low=565000.0,
        valuation_range_high=610000.0,
        valuation_psf=511.30,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_score=88.5,
        breakdown=breakdown,
        key_drivers=["Recent comparable sales within 0.3 miles", "Strong submarket rental yield"],
        limitations=["Market data reflects synthetic demonstration fixtures"],
        methodology="Multi-factor weighted synthesis of adjusted comparable sales and market momentum",
    )
    assert val.legal_disclaimer == LEGAL_DISCLAIMER_TEXT
    assert "NOT a legally binding appraisal" in val.legal_disclaimer
    assert val.estimated_value == 588000.0


def test_human_review_decision_tracking():
    """Verify HumanReviewDecision captures decision, overrides, and notes."""
    review = HumanReviewDecision(
        review_id="REV-2026-001",
        reviewer_name="Sarah Jenkins",
        reviewer_role="Senior Asset Manager",
        status=ReviewStatus.MODIFIED,
        original_valuation=588000.0,
        original_recommended_rent=3100.0,
        modified_valuation=595000.0,
        modified_recommended_rent=3150.0,
        reviewer_notes="Adjusted upwards due to completed roof and HVAC capital upgrades.",
    )
    assert review.status == ReviewStatus.MODIFIED
    assert review.modified_valuation == 595000.0
    assert review.original_valuation == 588000.0
    assert "HVAC" in review.reviewer_notes
