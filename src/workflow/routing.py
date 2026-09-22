"""Conditional routing logic and loop protection for LangGraph multi-agent workflow."""

from src.core.enums import ReviewStatus
from src.core.state import AgentWorkflowState


def route_after_cma(state: AgentWorkflowState) -> str:
    """Conditional router after CMA: checks requires_more_evidence flag respecting step budget."""
    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", 15)

    # Infinite loop protection
    if step_count >= max_steps:
        return "market_conditions"

    if state.get("requires_more_evidence", False):
        return "market_data"

    return "market_conditions"


def route_after_human_review(state: AgentWorkflowState) -> str:
    """Conditional router after human review stage: handles APPROVE, MODIFY, REJECT, and EVIDENCE_REQUESTED."""
    review = state.get("human_review")

    # If review is pending or not yet submitted by user, halt and wait for human action
    if review is None or review.status == ReviewStatus.PENDING:
        return "end_wait_for_human"

    # Completed human actions route to final report sealing
    if review.status in [ReviewStatus.APPROVED, ReviewStatus.MODIFIED, ReviewStatus.REJECTED]:
        return "final_report"

    # If human requested more evidence: loop back to evidence acquisition with loop budget
    if review.status == ReviewStatus.EVIDENCE_REQUESTED:
        ev_count = state.get("evidence_request_count", 0)
        step_count = state.get("step_count", 0)
        max_steps = state.get("max_steps", 15)

        if step_count >= max_steps or ev_count >= 3:
            # Step budget exhausted -> cannot gather more without exceeding safety boundary
            state["workflow_status"] = "STEP_BUDGET_EXHAUSTED"
            return "final_report"

        return "market_data"

    return "final_report"
