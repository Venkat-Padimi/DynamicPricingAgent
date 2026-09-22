"""LangGraph multi-agent workflow graph assembly and orchestration."""

from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from src.core.enums import ReviewStatus
from src.core.models import HumanReviewDecision
from src.core.state import AgentWorkflowState
from src.workflow.nodes import (
    cma_node,
    dynamic_pricing_node,
    final_report_node,
    human_review_node,
    lease_rentroll_node,
    market_conditions_node,
    market_data_node,
    property_intake_node,
    risk_quality_node,
    valuation_node,
)
from src.workflow.routing import route_after_cma, route_after_human_review


def build_workflow_graph() -> Any:
    """Assemble and compile the stateful LangGraph multi-agent pipeline."""
    graph = StateGraph(AgentWorkflowState)

    # 1. Register specialized agent nodes
    graph.add_node("property_intake", property_intake_node)
    graph.add_node("market_data", market_data_node)
    graph.add_node("cma", cma_node)
    graph.add_node("market_conditions", market_conditions_node)
    graph.add_node("lease_rentroll", lease_rentroll_node)
    graph.add_node("valuation", valuation_node)
    graph.add_node("dynamic_pricing", dynamic_pricing_node)
    graph.add_node("risk_quality", risk_quality_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("final_report", final_report_node)

    # 2. Add linear and conditional edges
    graph.add_edge(START, "property_intake")
    graph.add_edge("property_intake", "market_data")
    graph.add_edge("market_data", "cma")

    # Conditional edge after CMA: expand radius if comps < 3
    graph.add_conditional_edges(
        "cma",
        route_after_cma,
        {
            "market_data": "market_data",
            "market_conditions": "market_conditions",
        },
    )

    graph.add_edge("market_conditions", "lease_rentroll")
    graph.add_edge("lease_rentroll", "valuation")
    graph.add_edge("valuation", "dynamic_pricing")
    graph.add_edge("dynamic_pricing", "risk_quality")
    graph.add_edge("risk_quality", "human_review")

    # Conditional edge after Human Review: pause for human, route to final report, or request evidence
    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "end_wait_for_human": END,
            "final_report": "final_report",
            "market_data": "market_data",
        },
    )

    graph.add_edge("final_report", END)

    return graph.compile()


# Singleton compiled graph
_COMPILED_APP = None


def get_compiled_app() -> Any:
    """Return singleton compiled LangGraph application."""
    global _COMPILED_APP
    if _COMPILED_APP is None:
        _COMPILED_APP = build_workflow_graph()
    return _COMPILED_APP


def run_pipeline(
    raw_input: Dict[str, Any],
    initial_radius_miles: float = 1.5,
    max_steps: int = 15,
) -> AgentWorkflowState:
    """Execute the multi-agent pipeline up to the mandatory Human Review stage."""
    app = get_compiled_app()

    initial_state: AgentWorkflowState = {
        "property_input": raw_input,
        "search_radius_miles": initial_radius_miles,
        "step_count": 0,
        "max_steps": max_steps,
        "evidence_request_count": 0,
        "audit_trail": [],
        "workflow_status": "INITIALIZED",
        "human_review": None,
    }

    # Execute graph synchronously
    result_state = app.invoke(initial_state)
    return result_state


def submit_human_decision(
    state: AgentWorkflowState,
    decision: HumanReviewDecision,
) -> AgentWorkflowState:
    """Resume and finalize workflow with human review decision."""
    app = get_compiled_app()

    # Inject decision into state
    updated_state: AgentWorkflowState = dict(state)
    updated_state["human_review"] = decision

    # Re-invoke graph from current state
    final_state = app.invoke(updated_state)
    return final_state
