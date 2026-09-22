"""LangGraph workflow node implementations for multi-agent coordination."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.comparable_engine import CMAEngine
from src.core.enums import ReviewStatus
from src.core.human_review_engine import HumanReviewEngine
from src.core.intake_engine import PropertyIntakeEngine
from src.core.lease_engine import LeaseAnalysisEngine
from src.core.market_conditions_engine import MarketConditionsEngine
from src.core.models import (
    AuditEntry,
    HumanReviewDecision,
    PropertyProfile,
)
from src.core.pricing_engine import DeterministicPricingEngine
from src.core.risk_engine import RiskQualityEngine
from src.core.state import AgentWorkflowState
from src.core.valuation_engine import DeterministicValuationEngine
from src.data.providers.base import BaseMarketDataProvider, BaseRentRollProvider
from src.data.providers.synthetic_provider import (
    SyntheticMarketDataProvider,
    SyntheticRentRollProvider,
)

# Global default provider instances for offline operation
_DEFAULT_MARKET_PROVIDER: BaseMarketDataProvider = SyntheticMarketDataProvider()
_DEFAULT_RENTROLL_PROVIDER: BaseRentRollProvider = SyntheticRentRollProvider()


def _log_audit_entry(
    state: AgentWorkflowState,
    agent_name: str,
    action: str,
    inputs_summary: str,
    outputs_summary: str,
    sources_consulted: List[str],
    start_time: float,
    warnings_issued: Optional[List[str]] = None,
    decision: Optional[str] = None,
) -> None:
    """Helper to record immutable audit trail entries."""
    if "audit_trail" not in state or state["audit_trail"] is None:
        state["audit_trail"] = []

    step_idx = len(state["audit_trail"]) + 1
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    entry = AuditEntry(
        step_index=step_idx,
        timestamp=datetime.now(timezone.utc),
        agent_name=agent_name,
        action=action,
        inputs_summary=inputs_summary,
        outputs_summary=outputs_summary,
        sources_consulted=sources_consulted,
        execution_time_ms=duration_ms,
        warnings_issued=warnings_issued or [],
        decision=decision,
    )
    state["audit_trail"].append(entry)
    state["step_count"] = state.get("step_count", 0) + 1


def property_intake_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Property Intake Agent: Normalizes and validates subject property profile."""
    t0 = time.perf_counter()
    raw_input = state.get("property_input", {})

    try:
        profile = PropertyIntakeEngine.parse_and_validate(raw_input)
        state["property_profile"] = profile
        state["search_radius_miles"] = state.get("search_radius_miles", 1.5)
        state["step_count"] = state.get("step_count", 0)
        state["max_steps"] = state.get("max_steps", 15)
        state["evidence_request_count"] = state.get("evidence_request_count", 0)
        state["workflow_status"] = "PROPERTY_INTAKE_COMPLETE"

        _log_audit_entry(
            state=state,
            agent_name="Property Intake Agent",
            action="PARSE_AND_VALIDATE",
            inputs_summary=f"Raw inputs for '{profile.address}, {profile.city}' ({profile.sqft:,.0f} sqft, {profile.property_type.value})",
            outputs_summary=f"Normalized PropertyProfile created with ID '{profile.property_id}'",
            sources_consulted=["User Intake Form"],
            start_time=t0,
        )
    except Exception as e:
        state["error_message"] = str(e)
        state["workflow_status"] = "ERROR_PROPERTY_INTAKE"
        _log_audit_entry(
            state=state,
            agent_name="Property Intake Agent",
            action="VALIDATION_FAILED",
            inputs_summary=str(raw_input),
            outputs_summary=f"Failed with error: {e}",
            sources_consulted=[],
            start_time=t0,
            warnings_issued=[str(e)],
        )

    return state


def market_data_node(
    state: AgentWorkflowState,
    market_provider: Optional[BaseMarketDataProvider] = None,
) -> AgentWorkflowState:
    """Market Data Agent: Queries comparable sales and rental records with provenance."""
    t0 = time.perf_counter()
    profile = state.get("property_profile")
    if not profile:
        return state

    provider = market_provider or _DEFAULT_MARKET_PROVIDER
    radius = state.get("search_radius_miles", 1.5)

    sales = provider.get_sales_comps(
        city=profile.city,
        zip_code=profile.zip_code,
        property_type=profile.property_type,
        max_distance_miles=radius,
        limit=12,
    )
    rentals = provider.get_rental_comps(
        city=profile.city,
        zip_code=profile.zip_code,
        property_type=profile.property_type,
        max_distance_miles=radius,
        limit=10,
    )

    state["sales_records"] = sales
    state["rental_records"] = rentals

    warnings = []
    if len(sales) < 3:
        warnings.append(f"Low sales comparable count ({len(sales)} within {radius:.1f} mi).")

    _log_audit_entry(
        state=state,
        agent_name="Market Data Agent",
        action="RETRIEVE_COMPARABLES",
        inputs_summary=f"Query {profile.city} (zip {profile.zip_code}, radius <= {radius:.1f} mi)",
        outputs_summary=f"Retrieved {len(sales)} sales records, {len(rentals)} rental records",
        sources_consulted=[provider.provider_name],
        start_time=t0,
        warnings_issued=warnings,
    )
    return state


def cma_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Comparable Property / CMA Agent: Scores similarity, adjusts features, and detects outliers."""
    t0 = time.perf_counter()
    profile = state.get("property_profile")
    sales = state.get("sales_records", [])
    if not profile:
        return state

    cma_engine = CMAEngine(min_similarity_threshold=0.45, max_comps_to_select=6)
    comps, cma_analysis = cma_engine.generate_cma(profile, sales)

    state["comparables"] = comps
    state["cma_analysis"] = cma_analysis

    # Auto-expansion if insufficient comps
    radius = state.get("search_radius_miles", 1.5)
    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", 15)
    if len(comps) < 3 and radius < 4.5 and step_count < max_steps:
        state["search_radius_miles"] = round(radius + 1.5, 1)
        state["requires_more_evidence"] = True
    else:
        state["requires_more_evidence"] = False

    warnings = []
    if cma_analysis.outlier_count > 0:
        warnings.append(f"{cma_analysis.outlier_count} outlier(s) detected during CMA.")
    if len(comps) < 3:
        warnings.append(f"Only {len(comps)} comparables qualified after similarity filtering.")

    _log_audit_entry(
        state=state,
        agent_name="CMA Agent",
        action="GENERATE_CMA",
        inputs_summary=f"{len(sales)} sales records evaluated against subject {profile.property_id}",
        outputs_summary=(
            f"Selected {len(comps)} comps; Adjusted median: ₹{cma_analysis.adjusted_median_price:,.0f} "
            f"(₹{cma_analysis.adjusted_psf_mean:,.0f}/sq ft)"
        ),
        sources_consulted=["CMA Engine v1.0"],
        start_time=t0,
        warnings_issued=warnings,
    )
    return state


def market_conditions_node(
    state: AgentWorkflowState,
    market_provider: Optional[BaseMarketDataProvider] = None,
) -> AgentWorkflowState:
    """Market Conditions Agent: Analyzes macro trends and submarket momentum."""
    t0 = time.perf_counter()
    profile = state.get("property_profile")
    if not profile:
        return state

    provider = market_provider or _DEFAULT_MARKET_PROVIDER
    conditions = provider.get_market_trends(profile.city, time_horizon_months=24)
    state["market_conditions"] = conditions

    summary = (
        f"{conditions.submarket_name}: {conditions.annual_price_growth_rate:+.1f}%/yr price growth, "
        f"{conditions.current_gross_yield_pct:.2f}% gross yield ({conditions.trend_direction.value})"
        if conditions
        else "No submarket trend data available"
    )

    _log_audit_entry(
        state=state,
        agent_name="Market Conditions Agent",
        action="ANALYZE_SUBMARKET_TRENDS",
        inputs_summary=f"Submarket analysis for city '{profile.city}'",
        outputs_summary=summary,
        sources_consulted=[provider.provider_name],
        start_time=t0,
    )
    return state


def lease_rentroll_node(
    state: AgentWorkflowState,
    rentroll_provider: Optional[BaseRentRollProvider] = None,
) -> AgentWorkflowState:
    """Lease & Rent-Roll Agent: Processes in-place lease schedule and occupancy metrics."""
    t0 = time.perf_counter()
    profile = state.get("property_profile")
    if not profile:
        return state

    provider = rentroll_provider or _DEFAULT_RENTROLL_PROVIDER
    units = provider.get_rent_roll(profile.property_id)
    summary = LeaseAnalysisEngine.analyze_rent_roll(profile.property_id, units)

    state["rent_roll_units"] = units
    state["rent_roll_summary"] = summary

    warnings = []
    if not summary:
        warnings.append("No active rent roll found. Rental pricing will use market baseline.")
        out_summary = "Zero units on file; rent roll marked as empty."
    else:
        out_summary = (
            f"{summary.occupied_units}/{summary.total_units} units occupied ({summary.physical_occupancy_rate*100:.1f}%), "
            f"₹{summary.current_in_place_monthly_rent:,.0f}/mo in-place rent. Cliff risk: {summary.cliff_risk_level}"
        )
        if summary.cliff_risk_level == "HIGH":
            warnings.append(f"High lease cliff rollover: {summary.lease_turnover_exposure_pct:.1f}% expiring in 90 days.")

    _log_audit_entry(
        state=state,
        agent_name="Lease & Rent-Roll Agent",
        action="ANALYZE_OPERATIONS",
        inputs_summary=f"Rent roll check for '{profile.property_id}'",
        outputs_summary=out_summary,
        sources_consulted=[provider.provider_name],
        start_time=t0,
        warnings_issued=warnings,
    )
    return state


def valuation_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Valuation Agent: Generates deterministic multi-component property valuation."""
    t0 = time.perf_counter()
    profile = state.get("property_profile")
    comps = state.get("comparables", [])
    cma = state.get("cma_analysis")
    trends = state.get("market_conditions")
    roll = state.get("rent_roll_summary")

    if not profile or not cma:
        return state

    val_engine = DeterministicValuationEngine()
    valuation_res = val_engine.calculate_valuation(
        subject=profile,
        comparables=comps,
        cma_analysis=cma,
        market_conditions=trends,
        rent_roll_summary=roll,
    )

    state["valuation"] = valuation_res

    _log_audit_entry(
        state=state,
        agent_name="Valuation Agent",
        action="CALCULATE_VALUATION",
        inputs_summary=f"CMA median ₹{cma.adjusted_median_price:,.0f} + {len(comps)} comps + trend & income components",
        outputs_summary=(
            f"Estimated Value: ₹{valuation_res.estimated_value:,.0f} "
            f"(₹{valuation_res.valuation_range_low:,.0f} – ₹{valuation_res.valuation_range_high:,.0f}, "
            f"₹{valuation_res.valuation_psf:.0f}/sq ft, Confidence: {valuation_res.confidence_level.value})"
        ),
        sources_consulted=["Deterministic Valuation Engine v1.0"],
        start_time=t0,
        warnings_issued=valuation_res.limitations,
    )
    return state


def dynamic_pricing_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Dynamic Pricing Agent: Generates deterministic rental recommendation and gap analysis."""
    t0 = time.perf_counter()
    profile = state.get("property_profile")
    rentals = state.get("rental_records", [])
    trends = state.get("market_conditions")
    roll = state.get("rent_roll_summary")

    if not profile:
        return state

    pricing_engine = DeterministicPricingEngine()
    pricing_res = pricing_engine.calculate_rental_pricing(
        subject=profile,
        rental_records=rentals,
        market_conditions=trends,
        rent_roll_summary=roll,
    )

    state["rental_pricing"] = pricing_res

    _log_audit_entry(
        state=state,
        agent_name="Dynamic Pricing Agent",
        action="CALCULATE_RENTAL_PRICING",
        inputs_summary=f"{len(rentals)} rental comps + occupancy & lease cliff factors",
        outputs_summary=(
            f"Recommended Rent Midpoint: ₹{pricing_res.recommended_midpoint:,.0f}/mo "
            f"(₹{pricing_res.recommended_rent_range_low:,.0f} – ₹{pricing_res.recommended_rent_range_high:,.0f}/mo)"
        ),
        sources_consulted=["Deterministic Pricing Engine v1.0"],
        start_time=t0,
    )
    return state


def risk_quality_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Risk & Data Quality Agent: Comprehensive audit of data freshness, variance, and cliffs."""
    t0 = time.perf_counter()
    profile = state.get("property_profile")
    comps = state.get("comparables", [])
    cma = state.get("cma_analysis")
    trends = state.get("market_conditions")
    roll = state.get("rent_roll_summary")
    val = state.get("valuation")
    pricing = state.get("rental_pricing")

    if not profile:
        return state

    report = RiskQualityEngine.evaluate_risks(
        subject=profile,
        comparables=comps,
        cma_analysis=cma,
        market_conditions=trends,
        rent_roll_summary=roll,
        valuation=val,
        rental_pricing=pricing,
    )

    state["risk_report"] = report

    _log_audit_entry(
        state=state,
        agent_name="Risk & Data Quality Agent",
        action="AUDIT_RISK_AND_QUALITY",
        inputs_summary=f"Full dataset audit across {len(comps)} sales comps, rent roll, and valuation metrics",
        outputs_summary=f"Overall Severity: {report.overall_risk_severity.value}, Data Quality Score: {report.data_quality_score:.1f}/100",
        sources_consulted=["Risk Assessment Engine v1.0"],
        start_time=t0,
        warnings_issued=[it.message for it in report.items if it.severity.value in ["HIGH", "CRITICAL"]],
    )
    return state


def human_review_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Human Review Agent: Enforces mandatory human approval gate before final pricing decision."""
    t0 = time.perf_counter()
    val = state.get("valuation")
    pricing = state.get("rental_pricing")
    review = state.get("human_review")

    if not val or not pricing:
        return state

    if review is None or review.status == ReviewStatus.PENDING:
        # Pause state at human review gate
        state["workflow_status"] = "WAITING_FOR_HUMAN_REVIEW"
        _log_audit_entry(
            state=state,
            agent_name="Human Review Agent",
            action="PAUSE_FOR_HUMAN_APPROVAL",
            inputs_summary=f"AI Valuation: ₹{val.estimated_value:,.0f}, AI Rent: ₹{pricing.recommended_midpoint:,.0f}/mo",
            outputs_summary="Workflow paused: Human-in-the-Loop review is required before decision finalization.",
            sources_consulted=[],
            start_time=t0,
            decision="PENDING_HUMAN_ACTION",
        )
    else:
        # Human decision provided
        state["workflow_status"] = f"REVIEW_{review.status.value}"
        if review.status == ReviewStatus.EVIDENCE_REQUESTED:
            state["search_radius_miles"] = state.get("search_radius_miles", 1.5) + 1.0
            state["evidence_request_count"] = state.get("evidence_request_count", 0) + 1

        _log_audit_entry(
            state=state,
            agent_name="Human Review Agent",
            action=f"RECORD_DECISION_{review.status.value}",
            inputs_summary=f"Reviewer: {review.reviewer_name} ({review.reviewer_role})",
            outputs_summary=(
                f"Decision: {review.status.value}. Notes: '{review.reviewer_notes}'. "
                f"Overrides: Val=₹{review.modified_valuation or val.estimated_value:,.0f}, "
                f"Rent=₹{review.modified_recommended_rent or pricing.recommended_midpoint:,.0f}/mo"
            ),
            sources_consulted=["Human Review Console"],
            start_time=t0,
            decision=review.status.value,
        )

    return state


def final_report_node(state: AgentWorkflowState) -> AgentWorkflowState:
    """Final Report Agent: Seals workflow outcome, final decision, and immutable audit trace."""
    t0 = time.perf_counter()
    review = state.get("human_review")
    status = state.get("workflow_status", "")

    if review and review.status == ReviewStatus.APPROVED:
        final_status = "COMPLETED_APPROVED"
        desc = "Recommendation finalized and approved by human reviewer."
    elif review and review.status == ReviewStatus.MODIFIED:
        final_status = "COMPLETED_MODIFIED"
        desc = "Recommendation finalized with human reviewer adjustments."
    elif review and review.status == ReviewStatus.REJECTED:
        final_status = "HALTED_REJECTED"
        desc = "Recommendation rejected by human reviewer; pricing finalization stopped."
    elif state.get("step_count", 0) >= state.get("max_steps", 15):
        final_status = "HALTED_STEP_BUDGET_EXHAUSTED"
        desc = "Workflow halted: Maximum execution step budget exceeded."
    else:
        final_status = status or "COMPLETED_REVIEW_PENDING"
        desc = "Workflow completed processing; awaiting human sign-off."

    state["workflow_status"] = final_status

    _log_audit_entry(
        state=state,
        agent_name="Final Report Agent",
        action="FINALIZE_WORKFLOW",
        inputs_summary=f"Status: {final_status}",
        outputs_summary=desc,
        sources_consulted=["Audit Logger"],
        start_time=t0,
        decision=final_status,
    )
    return state
