"""Unit tests for Phase 9 Compliance Dossier Reporter and JSON Export engine."""

import json
from datetime import datetime, timezone
import pytest

from src.core.enums import ConfidenceLevel, PropertyCondition, PropertyType, ReviewStatus, RiskSeverity
from src.core.models import (
    LEGAL_DISCLAIMER_TEXT,
    SYNTHETIC_NOTICE_TEXT,
    AuditEntry,
    HumanReviewDecision,
    PropertyProfile,
)
from src.core.state import AgentWorkflowState
from src.reporting.reporter import (
    ComplianceDossierReporter,
    generate_json_dict,
    generate_json_export,
    generate_markdown_dossier,
)
from src.workflow.graph import run_pipeline, submit_human_decision


@pytest.fixture
def austin_demo_input():
    return {
        "property_id": "PROP-ATX-001",
        "address": "1208 Colorado St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "property_type": "Condo",
        "sqft": 1150.0,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "year_built": 2019,
        "condition": "Excellent",
        "amenities": ["Pool", "Gym", "Concierge", "Balcony"],
        "parking_spaces": 1,
    }


@pytest.fixture
def active_pipeline_state(austin_demo_input):
    """Run pipeline up to Human Review stage."""
    return run_pipeline(austin_demo_input, initial_radius_miles=1.5)


def test_markdown_dossier_required_sections_and_disclaimers(active_pipeline_state):
    """Verify generated Markdown dossier contains all mandatory compliance sections and disclaimers."""
    dossier = generate_markdown_dossier(active_pipeline_state)

    assert isinstance(dossier, str)
    assert len(dossier) > 3000

    # 1. Mandatory Disclaimers
    assert LEGAL_DISCLAIMER_TEXT in dossier
    assert SYNTHETIC_NOTICE_TEXT in dossier
    assert "MANDATORY LEGAL & DECISION-SUPPORT DISCLAIMER" in dossier
    assert "DATA PROVENANCE & SYNTHETIC DEMONSTRATION DISCLOSURE" in dossier
    assert "decision-support" in dossier.lower()

    # 2. Executive Valuation & Pricing Summary
    assert "## 1. Executive Summary & Recommendation Overview" in dossier
    assert "Estimated Market Value" in dossier
    assert "Valuation Range" in dossier
    assert "Price per Sq Ft" in dossier
    assert "Confidence Level" in dossier
    assert "Deterministic Component Weight Allocation" in dossier
    assert "Floor Rate" in dossier
    assert "Recommended Midpoint" in dossier
    assert "Ceiling Rate" in dossier

    # 3. Subject Property Overview
    assert "## 2. Subject Property Overview & Specifications" in dossier
    assert "1208 Colorado St" in dossier
    assert "Austin, TX" in dossier
    assert "78701" in dossier
    assert "Super Built-up Area" in dossier or "Gross Living Area" in dossier

    # 4. Provenance Matrix
    assert "## 3. Data Provenance & Source Integrity Matrix" in dossier
    assert "SYNTHETIC DEMONSTRATION DATA" in dossier
    assert "Sales Transactions" in dossier
    assert "Rental Transactions" in dossier
    assert "Operational Rent Roll" in dossier

    # 5. Comparative Market Analysis (CMA)
    assert "## 4. Comparative Market Analysis (CMA) & Feature Adjustments" in dossier
    assert "Selected Comparable Properties" in dossier
    assert "Step-by-Step Appraisal Feature Adjustments Breakdown" in dossier
    assert "Appraisal Directionality Rule" in dossier

    # 6. Submarket Trends
    assert "## 5. Submarket Conditions & Historical Trends" in dossier
    assert "Annual Sales Price CAGR" in dossier
    assert "Annual Rental Rate CAGR" in dossier
    assert "Gross Capitalization Yield" in dossier

    # 7. Operational Rent Roll & Expiration Cliff
    assert "## 6. Operational Rent Roll & Lease Expiration Analysis" in dossier
    assert "Physical Occupancy" in dossier
    assert "30 / 60 / 90-Day Lease Expiration Cliff Ladder" in dossier
    assert "Anonymized Tenant Rent Schedule" in dossier
    assert "TENANT-" in dossier  # PII Protection verification

    # 8. Risk Assessment Scorecard
    assert "## 7. Risk Assessment & Data Quality Scorecard" in dossier
    assert "Overall Risk Severity" in dossier
    assert "Composite Data Quality Score" in dossier

    # 9. Human Review Governance
    assert "## 8. Human-in-the-Loop Review Sign-Off & Governance" in dossier
    assert "Formal Human Reviewer Attestation" in dossier

    # 10. Audit Trail
    assert "## 9. Multi-Agent Execution Audit Log" in dossier
    assert "Property Intake Agent" in dossier
    assert "Valuation Agent" in dossier


def test_json_export_structure_and_serialization(active_pipeline_state):
    """Verify structured JSON payload contains complete serializable state and metadata."""
    json_str = generate_json_export(active_pipeline_state)
    assert isinstance(json_str, str)

    # Must parse as valid JSON
    data = json.loads(json_str)

    # Metadata checks
    assert "report_metadata" in data
    assert "report_id" in data["report_metadata"]
    assert data["report_metadata"]["platform_version"] == "1.0.0"
    assert data["report_metadata"]["disclaimers"]["legal_disclaimer"] == LEGAL_DISCLAIMER_TEXT
    assert data["report_metadata"]["disclaimers"]["synthetic_notice"] == SYNTHETIC_NOTICE_TEXT

    # Execution checks
    assert data["workflow_execution"]["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"
    assert data["workflow_execution"]["search_radius_miles"] == 1.5

    # Domain objects checks
    assert data["property_profile"]["property_id"] == "PROP-ATX-001"
    assert data["valuation"]["estimated_value"] > 0
    assert data["rental_pricing"]["recommended_midpoint"] > 0
    assert len(data["comparables"]) > 0
    assert len(data["audit_trail"]) >= 9
    assert len(data["provenance_matrix"]) >= 4

    # Ensure rent roll tenant pseudonymization in JSON
    for unit in data["rent_roll_units"]:
        assert unit["tenant_pseudonym"].startswith("TENANT-")
        assert "@" not in unit["tenant_pseudonym"]


def test_human_review_approval_decision_preservation(active_pipeline_state):
    """Verify Approved human review decision is properly reflected in both MD and JSON."""
    val = active_pipeline_state["valuation"]
    pricing = active_pipeline_state["rental_pricing"]

    decision = HumanReviewDecision(
        review_id="REV-TX-101",
        reviewer_name="Sarah Jenkins",
        reviewer_role="Senior Valuation Director",
        status=ReviewStatus.APPROVED,
        original_valuation=val.estimated_value,
        original_recommended_rent=pricing.recommended_midpoint,
        reviewer_notes="Model comps and adjustments verified against local submarket records. Approved.",
    )

    final_state = submit_human_decision(active_pipeline_state, decision)
    assert final_state["workflow_status"] == "COMPLETED_APPROVED"

    # Markdown checks
    md = generate_markdown_dossier(final_state)
    assert "APPROVED FOR PUBLISHING" in md
    assert "REV-TX-101" in md
    assert "Sarah Jenkins (Senior Valuation Director)" in md
    assert "Model comps and adjustments verified" in md

    # JSON checks
    data = generate_json_dict(final_state)
    assert data["workflow_execution"]["workflow_status"] == "COMPLETED_APPROVED"
    assert data["human_review"]["status"] == "APPROVED"
    assert data["human_review"]["reviewer_name"] == "Sarah Jenkins"


def test_human_review_modify_decision_with_overrides(active_pipeline_state):
    """Verify Modified human review decision captures custom overrides and justification in reports."""
    val = active_pipeline_state["valuation"]
    pricing = active_pipeline_state["rental_pricing"]

    modified_val = 625000.0
    modified_rent = 3300.0

    decision = HumanReviewDecision(
        review_id="REV-TX-102",
        reviewer_name="Marcus Vance",
        reviewer_role="Asset Manager",
        status=ReviewStatus.MODIFIED,
        original_valuation=val.estimated_value,
        original_recommended_rent=pricing.recommended_midpoint,
        modified_valuation=modified_val,
        modified_recommended_rent=modified_rent,
        reviewer_notes="Applied slight upward premium for renovated amenity floor and new school district zoning.",
    )

    final_state = submit_human_decision(active_pipeline_state, decision)
    assert final_state["workflow_status"] == "COMPLETED_MODIFIED"

    md = generate_markdown_dossier(final_state)
    assert "MODIFIED WITH REVIEWER OVERRIDES" in md
    assert "₹625,000" in md or "625,000" in md or "₹6.25 Lakh" in md
    assert "₹3,300" in md or "3,300" in md
    assert "Marcus Vance (Asset Manager)" in md
    assert "Applied slight upward premium" in md

    data = generate_json_dict(final_state)
    assert data["workflow_execution"]["workflow_status"] == "COMPLETED_MODIFIED"
    assert data["human_review"]["modified_valuation"] == modified_val
    assert data["human_review"]["modified_recommended_rent"] == modified_rent


def test_human_review_reject_decision(active_pipeline_state):
    """Verify Rejected human review decision properly halts finalization in reports."""
    val = active_pipeline_state["valuation"]
    pricing = active_pipeline_state["rental_pricing"]

    decision = HumanReviewDecision(
        review_id="REV-TX-103",
        reviewer_name="Elena Rostova",
        reviewer_role="Chief Risk Officer",
        status=ReviewStatus.REJECTED,
        original_valuation=val.estimated_value,
        original_recommended_rent=pricing.recommended_midpoint,
        reviewer_notes="Subject property has pending structural inspection litigation not captured in intake.",
    )

    final_state = submit_human_decision(active_pipeline_state, decision)
    assert final_state["workflow_status"] == "HALTED_REJECTED"

    md = generate_markdown_dossier(final_state)
    assert "REJECTED — PRICING HALTED" in md
    assert "Elena Rostova" in md
    assert "pending structural inspection litigation" in md

    data = generate_json_dict(final_state)
    assert data["workflow_execution"]["workflow_status"] == "HALTED_REJECTED"
    assert data["human_review"]["status"] == "REJECTED"


def test_deterministic_reproducibility():
    """Verify repeated report generations on identical state produce identical outputs."""
    profile = PropertyProfile(
        property_id="PROP-REPRO-001",
        address="500 Main St",
        city="Seattle",
        state="WA",
        zip_code="98101",
        property_type=PropertyType.SINGLE_FAMILY,
        sqft=2200.0,
        bedrooms=4,
        bathrooms=3.0,
        year_built=2015,
        condition=PropertyCondition.GOOD,
    )

    state: AgentWorkflowState = {
        "property_profile": profile,
        "workflow_status": "TESTING",
        "audit_trail": [],
        "comparables": [],
        "rent_roll_units": [],
    }

    reporter = ComplianceDossierReporter()

    md1 = reporter.generate_markdown_dossier(state)
    md2 = reporter.generate_markdown_dossier(state)

    # Note: timestamps inside header reflect current time, so check core body consistency
    # Split header lines and compare the substantive report body
    body1 = "\n".join(md1.split("\n")[4:])
    body2 = "\n".join(md2.split("\n")[4:])
    assert body1 == body2


def test_graceful_missing_and_partial_data_handling():
    """Verify reporter handles empty, missing, or partially executed state without crashing."""
    reporter = ComplianceDossierReporter()

    # 1. Completely empty state
    empty_state: AgentWorkflowState = {}
    md_empty = reporter.generate_markdown_dossier(empty_state)
    assert isinstance(md_empty, str)
    assert "Property profile not provided" in md_empty
    assert "Valuation calculation is not yet executed" in md_empty
    assert LEGAL_DISCLAIMER_TEXT in md_empty

    json_empty = reporter.generate_json_export(empty_state)
    dict_empty = json.loads(json_empty)
    assert dict_empty["property_profile"] is None
    assert dict_empty["valuation"] is None

    # 2. State with only property profile
    profile = PropertyProfile(
        property_id="PROP-MIN-001",
        address="100 Minimalist Ave",
        city="Miami",
        state="FL",
        zip_code="33101",
        property_type=PropertyType.CONDO,
        sqft=800.0,
        bedrooms=1,
        bathrooms=1.0,
        year_built=2021,
    )
    partial_state: AgentWorkflowState = {
        "property_profile": profile,
        "workflow_status": "INITIALIZED",
    }

    md_partial = reporter.generate_markdown_dossier(partial_state)
    assert "100 Minimalist Ave" in md_partial
    assert "Valuation calculation is not yet executed" in md_partial
    assert "AWAITING HUMAN ACTION" in md_partial
