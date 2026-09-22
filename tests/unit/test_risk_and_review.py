"""Unit tests for Risk Assessment Engine and Human Review Engine."""

import pytest
from src.core.enums import ConfidenceLevel, PropertyCondition, PropertyType, ReviewStatus, RiskSeverity
from src.core.human_review_engine import HumanReviewEngine
from src.core.models import (
    CMAAnalysis,
    ComparableProperty,
    MarketRecord,
    PropertyProfile,
    ProvenanceMetadata,
    RentalPricingBreakdown,
    RentalPricingResult,
    RentRollSummary,
    ValuationComponentBreakdown,
    ValuationResult,
)
from src.core.risk_engine import RiskQualityEngine


@pytest.fixture
def mock_subject():
    return PropertyProfile(
        property_id="PROP-RISK-001",
        address="100 Congress Ave",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        sqft=1200.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2020,
        condition=PropertyCondition.EXCELLENT,
    )


@pytest.fixture
def mock_valuation():
    return ValuationResult(
        property_id="PROP-RISK-001",
        estimated_value=600000.0,
        valuation_range_low=570000.0,
        valuation_range_high=630000.0,
        valuation_psf=500.0,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_score=85.0,
        breakdown=ValuationComponentBreakdown(
            cma_sales_component=600000.0,
            cma_weight=1.0,
        ),
        methodology="Test CMA",
    )


@pytest.fixture
def mock_rental_pricing():
    return RentalPricingResult(
        property_id="PROP-RISK-001",
        current_in_place_rent=3100.0,
        estimated_market_rent=3200.0,
        recommended_rent_range_low=3050.0,
        recommended_rent_range_high=3350.0,
        recommended_midpoint=3200.0,
        rent_gap_amount=100.0,
        rent_gap_percentage=3.2,
        confidence_level=ConfidenceLevel.HIGH,
        confidence_score=85.0,
        breakdown=RentalPricingBreakdown(base_market_comp_rent=3200.0),
    )


def test_risk_quality_engine_insufficient_comps(mock_subject):
    """Verify RiskQualityEngine flags insufficient or zero comparables."""
    # Zero comps -> CRITICAL
    report_zero = RiskQualityEngine.evaluate_risks(
        subject=mock_subject,
        comparables=[],
    )
    assert report_zero.is_insufficient_comps is True
    assert report_zero.overall_risk_severity == RiskSeverity.CRITICAL
    assert report_zero.data_quality_score <= 65.0

    # 1 comp -> HIGH severity
    prov = ProvenanceMetadata(source="Test", record_id="C1")
    rec = MarketRecord(
        record_id="C1", address="Addr", city="Austin", state="TX", zip_code="78701",
        property_type=PropertyType.CONDO, transaction_date="2025-10-01", sale_price=600000.0,
        sqft=1200.0, bedrooms=2, bathrooms=2.0, year_built=2020, provenance=prov,
    )
    comp = ComparableProperty(
        record=rec, similarity_score=0.9, adjusted_price=600000.0, adjusted_price_psf=500.0,
        selection_rationale="test",
    )
    report_one = RiskQualityEngine.evaluate_risks(
        subject=mock_subject,
        comparables=[comp],
    )
    assert report_one.is_insufficient_comps is True
    assert report_one.overall_risk_severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]


def test_risk_quality_engine_stale_data_and_variance(mock_subject):
    """Verify RiskQualityEngine detects stale records (>12 months) and high price variance."""
    prov = ProvenanceMetadata(source="Test", record_id="STALE")
    # Date in 2023 (more than 12 months ago)
    rec_stale = MarketRecord(
        record_id="STALE", address="Addr", city="Austin", state="TX", zip_code="78701",
        property_type=PropertyType.CONDO, transaction_date="2023-01-01", sale_price=500000.0,
        sqft=1200.0, bedrooms=2, bathrooms=2.0, year_built=2020, provenance=prov,
    )
    rec_fresh = MarketRecord(
        record_id="FRESH", address="Addr 2", city="Austin", state="TX", zip_code="78701",
        property_type=PropertyType.CONDO, transaction_date="2025-11-01", sale_price=800000.0,
        sqft=1200.0, bedrooms=2, bathrooms=2.0, year_built=2020, provenance=prov,
    )
    comps = [
        ComparableProperty(record=rec_stale, similarity_score=0.9, adjusted_price=500000.0, adjusted_price_psf=416.0, selection_rationale="test"),
        ComparableProperty(record=rec_fresh, similarity_score=0.9, adjusted_price=800000.0, adjusted_price_psf=666.0, selection_rationale="test"),
        ComparableProperty(record=rec_fresh, similarity_score=0.9, adjusted_price=520000.0, adjusted_price_psf=433.0, selection_rationale="test"),
    ]
    report = RiskQualityEngine.evaluate_risks(subject=mock_subject, comparables=comps)
    assert report.is_stale_data is True
    assert report.high_variance_warning is True
    assert any(it.category == "FRESHNESS" for it in report.items)
    assert any(it.category == "VARIANCE" for it in report.items)


def test_human_review_approve(mock_valuation, mock_rental_pricing):
    """Verify APPROVE action locks in validated recommendation without changes."""
    decision = HumanReviewEngine.approve_recommendation(
        reviewer_name="Marcus Vance",
        reviewer_role="Senior Acquisition Director",
        valuation=mock_valuation,
        rental_pricing=mock_rental_pricing,
        notes="All 5 comps verified against county deed records.",
    )
    assert decision.status == ReviewStatus.APPROVED
    assert decision.reviewer_name == "Marcus Vance"
    assert decision.original_valuation == 600000.0
    assert decision.original_recommended_rent == 3200.0
    assert decision.modified_valuation is None
    assert decision.modified_recommended_rent is None
    assert "verified" in decision.reviewer_notes


def test_human_review_modify_success(mock_valuation, mock_rental_pricing):
    """Verify MODIFY action correctly records overrides, original values, and mandatory rationale."""
    decision = HumanReviewEngine.modify_recommendation(
        reviewer_name="Elena Rostova",
        reviewer_role="Asset Manager",
        valuation=mock_valuation,
        rental_pricing=mock_rental_pricing,
        modified_valuation=615000.0,
        modified_recommended_rent=3300.0,
        notes="Adjusted upwards due to completed designer kitchen renovation and premium floor elevation.",
    )
    assert decision.status == ReviewStatus.MODIFIED
    assert decision.original_valuation == 600000.0
    assert decision.original_recommended_rent == 3200.0
    assert decision.modified_valuation == 615000.0
    assert decision.modified_recommended_rent == 3300.0
    assert "kitchen renovation" in decision.reviewer_notes


def test_human_review_modify_validation_enforcement(mock_valuation, mock_rental_pricing):
    """Verify MODIFY rejects missing notes, missing values, or negative numbers."""
    # Missing notes must fail
    with pytest.raises(ValueError, match="justification 'notes' are required"):
        HumanReviewEngine.modify_recommendation(
            reviewer_name="Elena Rostova",
            reviewer_role="Asset Manager",
            valuation=mock_valuation,
            rental_pricing=mock_rental_pricing,
            modified_valuation=615000.0,
            notes="",  # Blank notes forbidden
        )

    # Negative valuation must fail
    with pytest.raises(ValueError, match="'modified_valuation' must be positive"):
        HumanReviewEngine.modify_recommendation(
            reviewer_name="Elena Rostova",
            reviewer_role="Asset Manager",
            valuation=mock_valuation,
            rental_pricing=mock_rental_pricing,
            modified_valuation=-50000.0,
            notes="Bad override",
        )

    # Missing both overrides must fail
    with pytest.raises(ValueError, match="at least one override"):
        HumanReviewEngine.modify_recommendation(
            reviewer_name="Elena Rostova",
            reviewer_role="Asset Manager",
            valuation=mock_valuation,
            rental_pricing=mock_rental_pricing,
            notes="No numbers given",
        )


def test_human_review_reject(mock_valuation, mock_rental_pricing):
    """Verify REJECT action halts decision finalization and requires rationale."""
    decision = HumanReviewEngine.reject_recommendation(
        reviewer_name="David Chen",
        reviewer_role="Chief Risk Officer",
        valuation=mock_valuation,
        rental_pricing=mock_rental_pricing,
        rejection_reason="Comps did not account for major highway construction noise adjacent to subject building.",
    )
    assert decision.status == ReviewStatus.REJECTED
    assert "highway construction" in decision.reviewer_notes
    assert decision.original_valuation == 600000.0

    # Missing rejection reason must fail
    with pytest.raises(ValueError, match="'rejection_reason' notes are required"):
        HumanReviewEngine.reject_recommendation(
            reviewer_name="David Chen",
            reviewer_role="CRO",
            valuation=mock_valuation,
            rental_pricing=mock_rental_pricing,
            rejection_reason="",
        )


def test_human_review_request_more_evidence(mock_valuation, mock_rental_pricing):
    """Verify REQUEST_MORE_EVIDENCE action captures detailed evidence directives."""
    decision = HumanReviewEngine.request_more_evidence(
        reviewer_name="David Chen",
        reviewer_role="CRO",
        valuation=mock_valuation,
        rental_pricing=mock_rental_pricing,
        evidence_request_details="Expand search radius to 1.5 miles and incorporate closed sales from Q4 2025.",
    )
    assert decision.status == ReviewStatus.EVIDENCE_REQUESTED
    assert decision.evidence_request_details == "Expand search radius to 1.5 miles and incorporate closed sales from Q4 2025."
    assert decision.original_valuation == 600000.0
