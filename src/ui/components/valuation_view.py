"""Valuation summary cards, methodology, and legal disclaimers view component."""

from typing import Optional

import streamlit as st

from src.core.enums import ConfidenceLevel
from src.core.models import ValuationResult


def render_valuation_view(val: Optional[ValuationResult]) -> None:
    """Render institutional valuation summary cards and breakdown."""
    if not val:
        st.warning("⚠️ No valuation estimate available. Run the analysis to generate valuation.")
        return

    st.markdown("### 💰 Valuation Recommendation")

    # Main Metric Cards
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            label="Estimated Market Value",
            value=f"${val.estimated_value:,.0f}",
            help="Weighted deterministic synthesis of adjusted CMA sales, trend momentum, and yield capitalization.",
        )

    with c2:
        st.metric(
            label="Valuation Range",
            value=f"${val.valuation_range_low:,.0f} – ${val.valuation_range_high:,.0f}",
            help="Confidence-adjusted lower and upper empirical boundaries.",
        )

    with c3:
        st.metric(
            label="Valuation PSF",
            value=f"${val.valuation_psf:,.2f} / sqft",
        )

    with c4:
        color = "green" if val.confidence_level == ConfidenceLevel.HIGH else ("orange" if val.confidence_level == ConfidenceLevel.MEDIUM else "red")
        st.metric(
            label="Confidence Level",
            value=f"{val.confidence_level.value} ({val.confidence_score:.0f}/100)",
            help="Deterministic score based on comps count, similarity, distance, and variance.",
        )

    # Component Contribution Breakdown Table / Expander
    with st.expander("🔍 View Transparent Valuation Mathematical Breakdown", expanded=False):
        b = val.breakdown
        st.markdown(f"**Methodology:** `{val.methodology}`")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"- **CMA Sales Component ({b.cma_weight*100:.0f}% weight):** `${b.cma_sales_component:,.2f}`")
            st.markdown(f"- **Submarket Momentum Component ({b.market_trend_weight*100:.0f}% weight):** `${b.market_trend_component:,.2f}`")
            st.markdown(f"- **Micro-Location Factor ({b.location_weight*100:.0f}% weight):** `${b.location_component:,.2f}`")

        with col_b:
            if b.income_capitalization_component:
                st.markdown(f"- **Income Capitalization ({b.income_weight*100:.0f}% weight):** `${b.income_capitalization_component:,.2f}`")
            else:
                st.markdown("- **Income Capitalization:** `Not Applicable / 0% weight`")
            st.markdown(f"- **Data Quality Haircut:** `${b.data_quality_adjustment:,.2f}`")

        if val.key_drivers:
            st.markdown("##### Key Valuation Drivers:")
            for d in val.key_drivers:
                st.markdown(f"• {d}")

    # Legal Disclaimer Card
    st.caption(f"🔒 **Decision-Support Notice:** {val.legal_disclaimer}")
