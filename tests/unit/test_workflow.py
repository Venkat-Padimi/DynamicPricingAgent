"""Unit and integration tests for LangGraph multi-agent workflow orchestration."""

import pytest
from src.core.enums import ConfidenceLevel, ReviewStatus
from src.core.human_review_engine import HumanReviewEngine
from src.core.models import HumanReviewDecision
from src.core.state import AgentWorkflowState
from src.workflow.graph import run_pipeline, submit_human_decision
from src.workflow.routing import route_after_cma, route_after_human_review


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


def test_end_to_end_pipeline_pauses_at_human_review(austin_demo_input):
    """Verify entire agent graph executes cleanly and pauses at mandatory Human Review stage."""
    state = run_pipeline(austin_demo_input, initial_radius_miles=1.5)

    assert state["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"
    assert state["property_profile"] is not None
    assert state["property_profile"].property_id == "PROP-ATX-001"
    assert len(state["sales_records"]) > 0
    assert len(state["rental_records"]) > 0
    assert len(state["comparables"]) > 0
    assert state["cma_analysis"] is not None
    assert state["market_conditions"] is not None
    assert state["rent_roll_summary"] is not None
    assert state["valuation"] is not None
    assert state["valuation"].estimated_value > 0
    assert state["rental_pricing"] is not None
    assert state["rental_pricing"].recommended_midpoint > 0
    assert state["risk_report"] is not None

    # Audit trail must contain entries for all agent nodes executed
    agent_names = [e.agent_name for e in state["audit_trail"]]
    assert "Property Intake Agent" in agent_names
    assert "Market Data Agent" in agent_names
    assert "CMA Agent" in agent_names
    assert "Market Conditions Agent" in agent_names
    assert "Lease & Rent-Roll Agent" in agent_names
    assert "Valuation Agent" in agent_names
    assert "Dynamic Pricing Agent" in agent_names
    assert "Risk & Data Quality Agent" in agent_names
    assert "Human Review Agent" in agent_names

    # Check that execution times were recorded
    for entry in state["audit_trail"]:
        assert entry.execution_time_ms >= 0.0
        assert entry.timestamp is not None


def test_human_review_approval_flow(austin_demo_input):
    """Verify APPROVE action seals finalized recommendation and completes workflow."""
    state = run_pipeline(austin_demo_input)
    assert state["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"

    decision = HumanReviewEngine.approve_recommendation(
        reviewer_name="Sarah Jenkins",
        reviewer_role="Senior Asset Manager",
        valuation=state["valuation"],
        rental_pricing=state["rental_pricing"],
        notes="Comps inspected and verified; approved for publication.",
    )

    final_state = submit_human_decision(state, decision)
    assert final_state["workflow_status"] == "COMPLETED_APPROVED"
    assert final_state["human_review"].status == ReviewStatus.APPROVED

    final_entry = final_state["audit_trail"][-1]
    assert final_entry.agent_name == "Final Report Agent"
    assert "COMPLETED_APPROVED" in final_entry.decision


def test_human_review_modify_flow(austin_demo_input):
    """Verify MODIFY action applies overrides, preserves originals, and completes workflow."""
    state = run_pipeline(austin_demo_input)
    val = state["valuation"]
    pricing = state["rental_pricing"]

    decision = HumanReviewEngine.modify_recommendation(
        reviewer_name="Sarah Jenkins",
        reviewer_role="Senior Asset Manager",
        valuation=val,
        rental_pricing=pricing,
        modified_valuation=val.estimated_value + 15000.0,
        modified_recommended_rent=pricing.recommended_midpoint + 100.0,
        notes="Adjusted upwards due to completed private balcony and high floor view premium.",
    )

    final_state = submit_human_decision(state, decision)
    assert final_state["workflow_status"] == "COMPLETED_MODIFIED"
    assert final_state["human_review"].status == ReviewStatus.MODIFIED
    assert final_state["human_review"].modified_valuation == val.estimated_value + 15000.0
    assert final_state["human_review"].modified_recommended_rent == pricing.recommended_midpoint + 100.0


def test_human_review_reject_flow(austin_demo_input):
    """Verify REJECT action halts decision finalization and marks workflow as rejected."""
    state = run_pipeline(austin_demo_input)

    decision = HumanReviewEngine.reject_recommendation(
        reviewer_name="David Chen",
        reviewer_role="CRO",
        valuation=state["valuation"],
        rental_pricing=state["rental_pricing"],
        rejection_reason="Major title defect identified during preliminary review.",
    )

    final_state = submit_human_decision(state, decision)
    assert final_state["workflow_status"] == "HALTED_REJECTED"
    assert final_state["human_review"].status == ReviewStatus.REJECTED
    assert "title defect" in final_state["human_review"].reviewer_notes


def test_human_review_request_more_evidence_flow(austin_demo_input):
    """Verify REQUEST_MORE_EVIDENCE routes back to evidence gathering with widened radius."""
    state = run_pipeline(austin_demo_input)
    init_radius = state.get("search_radius_miles", 1.5)

    decision = HumanReviewEngine.request_more_evidence(
        reviewer_name="David Chen",
        reviewer_role="CRO",
        valuation=state["valuation"],
        rental_pricing=state["rental_pricing"],
        evidence_request_details="Expand radius by 1.0 mile to find additional comparable sales.",
    )

    resumed_state = submit_human_decision(state, decision)
    # Must have looped back to market data and increased search radius
    assert resumed_state["search_radius_miles"] > init_radius
    assert resumed_state["evidence_request_count"] >= 1


def test_cma_radius_expansion_routing():
    """Verify route_after_cma expands radius when comps < 3 and respects safety limits."""
    # Case 1: Insufficient comps flag set -> returns "market_data"
    state_sparse: AgentWorkflowState = {
        "requires_more_evidence": True,
        "search_radius_miles": 3.0,
        "step_count": 2,
        "max_steps": 15,
    }
    next_node = route_after_cma(state_sparse)
    assert next_node == "market_data"

    # Case 2: Sufficient comps (no more evidence needed) -> proceeds to "market_conditions"
    state_ok: AgentWorkflowState = {
        "requires_more_evidence": False,
        "search_radius_miles": 1.5,
        "step_count": 2,
        "max_steps": 15,
    }
    next_node2 = route_after_cma(state_ok)
    assert next_node2 == "market_conditions"

    # Case 3: Step budget exhausted -> proceeds to market_conditions without infinite looping
    state_budget: AgentWorkflowState = {
        "requires_more_evidence": True,
        "search_radius_miles": 1.5,
        "step_count": 15,
        "max_steps": 15,
    }
    next_node3 = route_after_cma(state_budget)
    assert next_node3 == "market_conditions"


def test_step_budget_exhaustion_in_human_review_loop():
    """Verify loop protection prevents infinite loops when evidence is repeatedly requested."""
    state_exhausted: AgentWorkflowState = {
        "human_review": HumanReviewDecision(
            review_id="R-1",
            reviewer_name="Test",
            status=ReviewStatus.EVIDENCE_REQUESTED,
            original_valuation=500000.0,
            original_recommended_rent=3000.0,
        ),
        "step_count": 15,
        "max_steps": 15,
        "evidence_request_count": 3,
    }
    next_node = route_after_human_review(state_exhausted)
    assert next_node == "final_report"
    assert state_exhausted["workflow_status"] == "STEP_BUDGET_EXHAUSTED"
