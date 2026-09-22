"""Human-in-the-Loop Review Console component enforcing decision oversight."""

from typing import Callable, Optional

import streamlit as st

from src.core.enums import ReviewStatus
from src.core.formatters import format_inr, format_psf, format_rent
from src.core.human_review_engine import HumanReviewEngine
from src.core.models import (
    HumanReviewDecision,
    RentalPricingResult,
    ValuationResult,
)
from src.core.state import AgentWorkflowState


def render_human_review_view(
    state: AgentWorkflowState,
    on_submit_decision: Callable[[HumanReviewDecision], None],
) -> None:
    """Render mandatory Human Review controls: Approve, Modify, Reject, and Request Evidence in INR."""
    st.markdown("### 🧑‍⚖️ Human-in-the-Loop Review Console")

    val: Optional[ValuationResult] = state.get("valuation")
    pricing: Optional[RentalPricingResult] = state.get("rental_pricing")
    review: Optional[HumanReviewDecision] = state.get("human_review")

    if not val or not pricing:
        st.warning("Valuation and pricing estimates must be computed before human review can be initiated.")
        return

    # Check current status
    if review and review.status != ReviewStatus.PENDING:
        # Display Decision Receipt
        status_colors = {
            ReviewStatus.APPROVED: ("🟢 APPROVED", "success"),
            ReviewStatus.MODIFIED: ("🟡 MODIFIED WITH OVERRIDES", "warning"),
            ReviewStatus.REJECTED: ("🔴 REJECTED — NOT FINALIZED", "error"),
            ReviewStatus.EVIDENCE_REQUESTED: ("🔄 EVIDENCE REQUESTED", "info"),
        }
        label, box_type = status_colors.get(review.status, (review.status.value, "info"))

        if box_type == "success":
            st.success(f"### Decision Status: {label}")
        elif box_type == "warning":
            st.warning(f"### Decision Status: {label}")
        elif box_type == "error":
            st.error(f"### Decision Status: {label}")
        else:
            st.info(f"### Decision Status: {label}")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Reviewer:** {review.reviewer_name}")
            st.markdown(f"**Role:** {review.reviewer_role}")
            st.markdown(f"**Timestamp:** `{review.decision_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`")

        with c2:
            st.markdown(f"**Original Valuation:** `{format_inr(review.original_valuation, use_words=True)}`")
            if review.modified_valuation:
                st.markdown(f"**Final Overridden Valuation:** `{format_inr(review.modified_valuation, use_words=True)}`")
            else:
                st.markdown(f"**Final Valuation:** `{format_inr(review.original_valuation, use_words=True)}`")

        with c3:
            st.markdown(f"**Original Rent:** `{format_rent(review.original_recommended_rent)}`")
            if review.modified_recommended_rent:
                st.markdown(f"**Final Overridden Rent:** `{format_rent(review.modified_recommended_rent)}`")
            else:
                st.markdown(f"**Final Rent:** `{format_rent(review.original_recommended_rent)}`")

        st.markdown(f"**Reviewer Justification Notes:**")
        st.info(f"\"{review.reviewer_notes}\"")

        if review.evidence_request_details:
            st.markdown(f"**Evidence Directives:** `{review.evidence_request_details}`")

        st.divider()
        st.caption("To revise this decision or re-evaluate, select a new property or clear review state.")
        return

    # Pending Review State
    st.warning(
        "✋ **HUMAN APPROVAL REQUIRED:** Autonomous publication of valuations or rental prices is strictly prohibited under institutional governance. "
        "A qualified asset manager or property analyst must review the evidence below and record an approval, modification, or rejection."
    )

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.info(
            f"**AI Valuation Estimate:** {format_inr(val.estimated_value, use_words=True)}\n\n"
            f"Range: {format_inr(val.valuation_range_low)} – {format_inr(val.valuation_range_high)} ({format_psf(val.valuation_psf)})\n\n"
            f"Confidence: {val.confidence_level.value} ({val.confidence_score:.0f}/100)"
        )
    with col_info2:
        st.info(
            f"**AI Recommended Rent:** {format_rent(pricing.recommended_midpoint)}\n\n"
            f"Range: {format_inr(pricing.recommended_rent_range_low)} – {format_inr(pricing.recommended_rent_range_high)} / mo\n\n"
            f"In-Place Rent: {format_rent(pricing.current_in_place_rent) if pricing.current_in_place_rent else 'Vacant / Unleased'}"
        )

    # Review Controls Tabs
    tab_app, tab_mod, tab_rej, tab_ev = st.tabs(
        ["✅ Approve", "✏️ Modify With Overrides", "🚫 Reject", "🔎 Request More Evidence"]
    )

    with tab_app:
        st.markdown("#### Approve AI Recommendation As-Is")
        st.markdown("Accept the deterministic valuation and dynamic pricing as decision-support baseline.")
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            app_name = st.text_input("Reviewer Name", value="Venkatesh Rao", key="app_name")
        with c_a2:
            app_role = st.text_input("Reviewer Role", value="Real Estate Investment Analyst", key="app_role")
        app_notes = st.text_area("Audit Notes (Optional)", value="Reviewed and validated against municipal registry records, local comps, and rent roll.", key="app_notes")

        if st.button("🚀 Approve Recommendation", type="primary", key="btn_approve"):
            try:
                decision = HumanReviewEngine.approve_recommendation(
                    reviewer_name=app_name,
                    reviewer_role=app_role,
                    valuation=val,
                    rental_pricing=pricing,
                    notes=app_notes,
                )
                on_submit_decision(decision)
                st.rerun()
            except Exception as e:
                st.error(f"Approval failed: {e}")

    with tab_mod:
        st.markdown("#### Apply Human Overrides")
        st.markdown("Modify the valuation or rental pricing with mandatory audit justification notes.")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            mod_name = st.text_input("Reviewer Name", value="Venkatesh Rao", key="mod_name")
            mod_val = st.number_input("Override Valuation (₹)", value=float(val.estimated_value), step=100000.0, key="mod_val")
        with c_m2:
            mod_role = st.text_input("Reviewer Role", value="Senior Asset Manager", key="mod_role")
            mod_rent = st.number_input("Override Recommended Rent (₹/mo)", value=float(pricing.recommended_midpoint), step=1000.0, key="mod_rent")

        mod_notes = st.text_area("Mandatory Justification Notes*", placeholder="Explain reason for override (e.g. premium corner balcony view, superior interior woodwork, recent Sub-Registrar transaction)...", key="mod_notes")

        if st.button("💾 Submit Modified Recommendation", type="primary", key="btn_modify"):
            try:
                decision = HumanReviewEngine.modify_recommendation(
                    reviewer_name=mod_name,
                    reviewer_role=mod_role,
                    valuation=val,
                    rental_pricing=pricing,
                    modified_valuation=mod_val,
                    modified_recommended_rent=mod_rent,
                    notes=mod_notes,
                )
                on_submit_decision(decision)
                st.rerun()
            except Exception as e:
                st.error(f"Modification failed: {e}")

    with tab_rej:
        st.markdown("#### Reject Recommendation")
        st.markdown("Reject the recommendation and halt decision finalization.")
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            rej_name = st.text_input("Reviewer Name", value="Venkatesh Rao", key="rej_name")
        with c_r2:
            rej_role = st.text_input("Reviewer Role", value="Chief Investment Officer", key="rej_role")
        rej_reason = st.text_area("Mandatory Rejection Rationale*", placeholder="State why this recommendation cannot be approved...", key="rej_reason")

        if st.button("❌ Reject & Halt Finalization", type="secondary", key="btn_reject"):
            try:
                decision = HumanReviewEngine.reject_recommendation(
                    reviewer_name=rej_name,
                    reviewer_role=rej_role,
                    valuation=val,
                    rental_pricing=pricing,
                    rejection_reason=rej_reason,
                )
                on_submit_decision(decision)
                st.rerun()
            except Exception as e:
                st.error(f"Rejection failed: {e}")

    with tab_ev:
        st.markdown("#### Request Additional Evidence")
        st.markdown("Signal the LangGraph multi-agent workflow to widen search radius and re-gather market evidence.")
        c_e1, c_e2 = st.columns(2)
        with c_e1:
            ev_name = st.text_input("Reviewer Name", value="Venkatesh Rao", key="ev_name")
        with c_e2:
            ev_role = st.text_input("Reviewer Role", value="Acquisition Analyst", key="ev_role")
        ev_details = st.text_area(
            "Evidence Gathering Directives*",
            value="Expand comparable search radius by 2.0 km and re-evaluate recent transactions in adjacent sectors.",
            key="ev_details",
        )

        if st.button("🔄 Request More Evidence & Re-Run", type="secondary", key="btn_evidence"):
            try:
                decision = HumanReviewEngine.request_more_evidence(
                    reviewer_name=ev_name,
                    reviewer_role=ev_role,
                    valuation=val,
                    rental_pricing=pricing,
                    evidence_request_details=ev_details,
                )
                on_submit_decision(decision)
                st.rerun()
            except Exception as e:
                st.error(f"Evidence request failed: {e}")
