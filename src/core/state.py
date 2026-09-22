"""LangGraph Agent Workflow State Definition."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from src.core.models import (
    AuditEntry,
    CMAAnalysis,
    ComparableProperty,
    HumanReviewDecision,
    MarketConditions,
    MarketRecord,
    PropertyProfile,
    RentalPricingResult,
    RentRollSummary,
    RentRollUnit,
    RiskReport,
    ValuationResult,
)


class AgentWorkflowState(TypedDict, total=False):
    """Shared state dictionary passed across all LangGraph nodes."""

    # Raw property input supplied by the user/intake
    property_input: Dict[str, Any]

    # Normalized property profile
    property_profile: Optional[PropertyProfile]

    # Market records retrieved
    sales_records: List[MarketRecord]
    rental_records: List[MarketRecord]
    search_radius_miles: float

    # CMA analysis
    comparables: List[ComparableProperty]
    cma_analysis: Optional[CMAAnalysis]

    # Market conditions and trends
    market_conditions: Optional[MarketConditions]

    # Operational rent roll
    rent_roll_units: List[RentRollUnit]
    rent_roll_summary: Optional[RentRollSummary]

    # Valuation and pricing outputs
    valuation: Optional[ValuationResult]
    rental_pricing: Optional[RentalPricingResult]

    # Risk assessment and data quality
    risk_report: Optional[RiskReport]

    # Human-in-the-Loop review record
    human_review: Optional[HumanReviewDecision]

    # Execution tracking and audit trail
    audit_trail: List[AuditEntry]
    step_count: int
    max_steps: int
    workflow_status: str
    requires_more_evidence: bool
    evidence_request_count: int
    error_message: Optional[str]
