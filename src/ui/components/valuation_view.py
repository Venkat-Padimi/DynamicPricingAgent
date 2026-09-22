"""Valuation summary cards, methodology, and Indian legal disclaimers view component."""

from typing import Optional

import streamlit as st

from src.core.enums import ConfidenceLevel
from src.core.formatters import format_inr, format_inr_short, format_psf
from src.core.models import ValuationResult


def render_valuation_view(val: Optional[ValuationResult]) -> None:
    """Render institutional valuation summary cards and breakdown in INR."""
    if not val:
        st.warning("⚠️ No valuation estimate available. Run the analysis to generate valuation.")
        return

    st.markdown("### 💰 Property Valuation Recommendation")

    # Main Metric Cards
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            label="Estimated Market Value",
            value=format_inr(val.estimated_value, use_words=True),
            help="Weighted deterministic synthesis of adjusted CMA sales, trend momentum, and yield capitalization in INR.",
        )

    with c2:
        st.metric(
            label="Valuation Range",
            value=f"{format_inr_short(val.valuation_range_low)} – {format_inr_short(val.valuation_range_high)}",
            help=f"Confidence-adjusted boundaries: {format_inr(val.valuation_range_low)} to {format_inr(val.valuation_range_high)}",
        )

    with c3:
        st.metric(
            label="Valuation PSF",
            value=format_psf(val.valuation_psf),
        )

    with c4:
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
            st.markdown(f"- **CMA Sales Component ({b.cma_weight*100:.0f}% weight):** `{format_inr(b.cma_sales_component, use_words=True)}`")
            st.markdown(f"- **Submarket Momentum Component ({b.market_trend_weight*100:.0f}% weight):** `{format_inr(b.market_trend_component, use_words=True)}`")
            st.markdown(f"- **Micro-Location Factor ({b.location_weight*100:.0f}% weight):** `{format_inr(b.location_component, use_words=True)}`")

        with col_b:
            if b.income_capitalization_component:
                st.markdown(f"- **Income Capitalization ({b.income_weight*100:.0f}% weight):** `{format_inr(b.income_capitalization_component, use_words=True)}`")
            else:
                st.markdown("- **Income Capitalization:** `Not Applicable / 0% weight`")
            st.markdown(f"- **Data Quality Haircut:** `{format_inr(b.data_quality_adjustment)}`")

        if val.key_drivers:
            st.markdown("##### Key Valuation Drivers:")
            for d in val.key_drivers:
                st.markdown(f"• {d}")

    # Legal Disclaimer Card
    st.caption(f"🔒 **Decision-Support Notice:** {val.legal_disclaimer}")
