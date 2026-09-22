"""Comprehensive End-to-End System Integration Tests for the Automated Valuation & Dynamic Pricing Platform."""

import json
import pytest

from src.core.enums import ReviewStatus
from src.core.models import (
    LEGAL_DISCLAIMER_TEXT,
    SYNTHETIC_NOTICE_TEXT,
    HumanReviewDecision,
)
from src.reporting.reporter import generate_json_dict, generate_json_export, generate_markdown_dossier
from src.workflow.graph import run_pipeline, submit_human_decision


@pytest.fixture
def seattle_demo_input():
    return {
        "property_id": "PROP-SEA-002",
        "address": "4512 8th Ave NE",
        "city": "Seattle",
        "state": "WA",
        "zip_code": "98105",
        "property_type": "SingleFamily",
        "sqft": 2400.0,
        "bedrooms": 4,
        "bathrooms": 2.5,
        "year_built": 2012,
        "condition": "Good",
        "amenities": ["Garage", "Fenced Yard", "Deck"],
        "parking_spaces": 2,
    }


def test_full_pipeline_end_to_end_lifecycle(seattle_demo_input):
    """Verify entire pipeline executes from property intake through to human approval and report export."""
    # 1. Execute pipeline up to Human Review
    state = run_pipeline(seattle_demo_input, initial_radius_miles=1.5)

    assert state["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"
    assert state["property_profile"] is not None
    assert state["property_profile"].city == "Seattle"
    assert state["valuation"] is not None
    assert state["rental_pricing"] is not None
    assert state["risk_report"] is not None
    assert len(state["audit_trail"]) >= 9

    # 2. Simulate Human Reviewer Approval
    val = state["valuation"]
    pricing = state["rental_pricing"]

    decision = HumanReviewDecision(
        review_id="REV-SEA-001",
        reviewer_name="David Thorne",
        reviewer_role="Regional Managing Director",
        status=ReviewStatus.APPROVED,
        original_valuation=val.estimated_value,
        original_recommended_rent=pricing.recommended_midpoint,
        reviewer_notes="CMA comp adjustments and 24-month trend momentum verified against local submarket records. Approved.",
    )

    final_state = submit_human_decision(state, decision)
    assert final_state["workflow_status"] == "COMPLETED_APPROVED"
    assert final_state["human_review"] is not None
    assert final_state["human_review"].status == ReviewStatus.APPROVED

    # 3. Generate Compliance Dossier & JSON Export
    md = generate_markdown_dossier(final_state)
    json_str = generate_json_export(final_state)
    data = json.loads(json_str)

    # 4. Assert Document Integrity
    assert "APPROVED FOR PUBLISHING" in md
    assert "David Thorne" in md
    assert LEGAL_DISCLAIMER_TEXT in md
    assert SYNTHETIC_NOTICE_TEXT in md
    assert data["workflow_execution"]["workflow_status"] == "COMPLETED_APPROVED"
    assert data["human_review"]["reviewer_name"] == "David Thorne"

    # 5. Assert Zero Tenant PII Leakage
    for unit in data.get("rent_roll_units", []):
        assert unit["tenant_pseudonym"].startswith("TENANT-")
        assert "@" not in unit["tenant_pseudonym"]


def test_pipeline_modification_lifecycle(seattle_demo_input):
    """Verify human reviewer modification override workflow."""
    state = run_pipeline(seattle_demo_input, initial_radius_miles=1.5)
    val = state["valuation"]
    pricing = state["rental_pricing"]

    override_val = 1150000.0
    override_rent = 4800.0

    decision = HumanReviewDecision(
        review_id="REV-SEA-MOD-01",
        reviewer_name="Rachel Evans",
        reviewer_role="Principal Appraiser",
        status=ReviewStatus.MODIFIED,
        original_valuation=val.estimated_value,
        original_recommended_rent=pricing.recommended_midpoint,
        modified_valuation=override_val,
        modified_recommended_rent=override_rent,
        reviewer_notes="Adjusted upward based on brand-new roof and kitchen remodeling completed in Q1.",
    )

    final_state = submit_human_decision(state, decision)
    assert final_state["workflow_status"] == "COMPLETED_MODIFIED"

    md = generate_markdown_dossier(final_state)
    assert "MODIFIED WITH REVIEWER OVERRIDES" in md
    assert "₹1,150,000" in md or "1,150,000" in md
    assert "₹4,800" in md or "4,800" in md

    dict_data = generate_json_dict(final_state)
    assert dict_data["human_review"]["modified_valuation"] == override_val
    assert dict_data["human_review"]["modified_recommended_rent"] == override_rent


def test_pipeline_determinism_across_multiple_runs(seattle_demo_input):
    """Verify that multiple consecutive runs with identical inputs produce identical deterministic financial calculations."""
    state1 = run_pipeline(seattle_demo_input, initial_radius_miles=1.5)
    state2 = run_pipeline(seattle_demo_input, initial_radius_miles=1.5)

    # Deterministic valuation equivalence
    assert state1["valuation"].estimated_value == state2["valuation"].estimated_value
    assert state1["valuation"].valuation_range_low == state2["valuation"].valuation_range_low
    assert state1["valuation"].valuation_range_high == state2["valuation"].valuation_range_high
    assert state1["valuation"].confidence_score == state2["valuation"].confidence_score

    # Deterministic rental pricing equivalence
    assert state1["rental_pricing"].recommended_midpoint == state2["rental_pricing"].recommended_midpoint
    assert state1["rental_pricing"].recommended_rent_range_low == state2["rental_pricing"].recommended_rent_range_low
    assert state1["rental_pricing"].recommended_rent_range_high == state2["rental_pricing"].recommended_rent_range_high

    # Deterministic CMA comparable adjusted prices
    comps1 = state1["comparables"]
    comps2 = state2["comparables"]
    assert len(comps1) == len(comps2)
    for c1, c2 in zip(comps1, comps2):
        assert c1.adjusted_price == c2.adjusted_price
        assert c1.similarity_score == c2.similarity_score
        assert c1.total_net_adjustment == c2.total_net_adjustment
