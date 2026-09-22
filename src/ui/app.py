"""Main Streamlit application for AI Real Estate Valuation & Dynamic Pricing Platform."""

import sys
from pathlib import Path

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st

from src.core.enums import ReviewStatus
from src.core.models import HumanReviewDecision
from src.ui.components.audit_view import render_audit_view
from src.ui.components.cma_view import render_cma_view
from src.ui.components.comps_view import render_comps_view
from src.ui.components.export_view import render_export_view
from src.ui.components.human_review_view import render_human_review_view
from src.ui.components.pricing_view import render_pricing_view
from src.ui.components.property_selector import DEMO_PROPERTIES, render_property_selector
from src.ui.components.rentroll_view import render_rentroll_view
from src.ui.components.risk_view import render_risk_view
from src.ui.components.trends_view import render_trends_view
from src.ui.components.valuation_view import render_valuation_view
from src.workflow.graph import run_pipeline, submit_human_decision

st.set_page_config(
    page_title="AI Real Estate Valuation & Dynamic Pricing (India)",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Institutional Executive Aesthetic
st.markdown(
    """
    <style>
    .main { background-color: #0b0f19; }
    .stMetric { background-color: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; }
    .stAlert { border-radius: 8px; }
    h1, h2, h3 { color: #f8fafc; font-family: 'Inter', sans-serif; font-weight: 600; }
    .disclosure-banner {
        background-color: #451a03;
        border: 1px solid #b45309;
        color: #fef3c7;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 13px;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main():
    # 1. Header & Mandatory Synthetic Data Disclosure
    st.markdown(
        """
        <div class="disclosure-banner">
            ⚠️ <b>DATA INTEGRITY DISCLOSURE:</b> This platform operates with strictly labeled <b>Synthetic Demonstration Data</b>
            across Indian metropolitan markets (Hyderabad, Bengaluru, Mumbai, Pune, Visakhapatnam, Delhi NCR, Chennai).
            Values, transactions, and trends are mathematical fixtures for institutional demonstration and are not real market records.
            This AI system is a decision-support tool and does not produce legally consequential or registered valuations under Indian law.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.title("🏢 AI Real Estate Valuation & Dynamic Pricing Intelligence (India)")
    st.caption("Autonomous multi-agent real-estate valuation, CMA adjustments, dynamic rental pricing, and enforced Human-in-the-Loop governance.")

    # 2. Sidebar Property Selection
    selected_property_input = render_property_selector()

    # Session State Initialization
    if "current_prop_id" not in st.session_state:
        st.session_state["current_prop_id"] = selected_property_input.get("property_id")
        st.session_state["pipeline_state"] = None

    # Detect property change
    if st.session_state["current_prop_id"] != selected_property_input.get("property_id"):
        st.session_state["current_prop_id"] = selected_property_input.get("property_id")
        st.session_state["pipeline_state"] = None

    col_btn, col_rst = st.sidebar.columns([3, 2])
    with col_btn:
        run_clicked = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
    with col_rst:
        reset_clicked = st.button("🔄 Reset", use_container_width=True)

    if reset_clicked:
        st.session_state["pipeline_state"] = None
        st.rerun()

    # Automatically run pipeline on first load or when button clicked
    if run_clicked or st.session_state["pipeline_state"] is None:
        with st.spinner("Executing LangGraph Multi-Agent Analysis Pipeline..."):
            initial_state = run_pipeline(selected_property_input)
            st.session_state["pipeline_state"] = initial_state

    state = st.session_state["pipeline_state"]
    profile = state.get("property_profile")

    if not profile:
        st.error(f"Pipeline error: {state.get('error_message', 'Failed to initialize property profile.')}")
        return

    # Subject Property Summary Banner
    locality_str = f" ({profile.locality})" if profile.locality else ""
    carpet_str = f", RERA Carpet: {profile.carpet_area_sqft:,.0f} sq ft" if profile.carpet_area_sqft else ""
    st.markdown(
        f"#### Asset Under Analysis: **{profile.address}, {profile.city}, {profile.state} (PIN: {profile.zip_code})** "
        f"· `{profile.property_type.value}` ({profile.bhk_display}, {profile.bathrooms:.0f} Bath, {profile.sqft:,.0f} sq ft built-up{locality_str}{carpet_str}, Built {profile.year_built})"
    )

    # Human Review Status Banner
    review = state.get("human_review")
    if not review or review.status == ReviewStatus.PENDING:
        st.warning(
            "⏳ **STATUS: AWAITING HUMAN REVIEW** — The AI has computed valuation and rental recommendations. "
            "Please review the evidence in the tabs below and record your final decision in the **Human Review Console**."
        )
    elif review.status == ReviewStatus.APPROVED:
        st.success(f"✅ **STATUS: APPROVED BY REVIEWER** ({review.reviewer_name}) — Recommendation validated for publishing.")
    elif review.status == ReviewStatus.MODIFIED:
        st.warning(f"✏️ **STATUS: MODIFIED BY REVIEWER** ({review.reviewer_name}) — Custom valuation/rent overrides applied.")
    elif review.status == ReviewStatus.REJECTED:
        st.error(f"❌ **STATUS: REJECTED BY REVIEWER** ({review.reviewer_name}) — Pricing decision halted.")
    elif review.status == ReviewStatus.EVIDENCE_REQUESTED:
        st.info(f"🔄 **STATUS: EVIDENCE REQUESTED** ({review.reviewer_name}) — Re-querying market data with expanded radius.")

    # 3. Main Dashboard Tabs
    tabs = st.tabs([
        "📊 Executive Summary",
        "🏘️ Comparables (CMA)",
        "📈 Market Trends",
        "🏢 Lease & Rent Roll",
        "⚠️ Risk & Data Quality",
        "🧑‍⚖️ Human Review Console",
        "📜 Agent Audit Trace",
        "📥 Dossier & Export",
    ])

    with tabs[0]:
        # Executive Summary Tab
        render_valuation_view(state.get("valuation"))
        st.divider()
        render_pricing_view(state.get("rental_pricing"))

    with tabs[1]:
        # Comparables and CMA Tab
        render_comps_view(
            comparables=state.get("comparables", []),
            subject_sqft=profile.sqft,
            subject_estimated_val=state.get("valuation").estimated_value if state.get("valuation") else None,
        )
        st.divider()
        render_cma_view(
            cma=state.get("cma_analysis"),
            comparables=state.get("comparables", []),
        )

    with tabs[2]:
        # Market Trends Tab
        render_trends_view(state.get("market_conditions"))

    with tabs[3]:
        # Lease & Rent Roll Tab
        render_rentroll_view(
            summary=state.get("rent_roll_summary"),
            units=state.get("rent_roll_units", []),
        )

    with tabs[4]:
        # Risk & Data Quality Tab
        render_risk_view(state.get("risk_report"))

    with tabs[5]:
        # Human Review Console Tab
        def handle_human_decision(decision: HumanReviewDecision):
            with st.spinner("Submitting human decision and updating workflow state..."):
                finalized_state = submit_human_decision(st.session_state["pipeline_state"], decision)
                st.session_state["pipeline_state"] = finalized_state

        render_human_review_view(
            state=state,
            on_submit_decision=handle_human_decision,
        )

    with tabs[6]:
        # Agent Audit Trail Tab
        render_audit_view(state.get("audit_trail", []))

    with tabs[7]:
        # Compliance Dossier & Data Export Tab
        render_export_view(state)


if __name__ == "__main__":
    main()
