"""Comparative Market Analysis (CMA) adjustment waterfall and statistics view component."""

from typing import List, Optional

import streamlit as st

from src.core.formatters import format_inr, format_inr_short
from src.core.models import CMAAnalysis, ComparableProperty
from src.ui.visualizations import plot_cma_waterfall


def render_cma_view(cma: Optional[CMAAnalysis], comparables: List[ComparableProperty]) -> None:
    """Render CMA summary statistics and interactive feature adjustment waterfall in INR."""
    st.markdown("### 📊 Comparative Market Analysis (CMA) Breakdown")

    if not cma or not comparables:
        st.info("No CMA analysis available.")
        return

    # 1. Summary Statistics Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Adjusted Median Price", format_inr(cma.adjusted_median_price, use_words=True))
    with c2:
        st.metric("Adjusted Mean Price", format_inr(cma.adjusted_mean_price, use_words=True))
    with c3:
        st.metric("Adjusted Price Spread", f"{format_inr_short(cma.adjusted_price_low)} – {format_inr_short(cma.adjusted_price_high)}")
    with c4:
        st.metric("Statistical Outliers", f"{cma.outlier_count} detected")

    st.markdown(f"**Methodology:** `{cma.methodology_notes}`")

    # 2. Interactive Comp Feature Adjustment Waterfall
    st.markdown("#### 🌊 Feature Adjustment Waterfall")
    comp_options = {f"{c.record.address} (Adj: {format_inr(c.adjusted_price)})": c for c in comparables}
    selected_label = st.selectbox("Select Comparable to Inspect Line-Item Adjustments:", list(comp_options.keys()))

    if selected_label:
        selected_comp = comp_options[selected_label]
        waterfall_fig = plot_cma_waterfall(selected_comp)
        st.plotly_chart(waterfall_fig, use_container_width=True)

        # Line-item adjustments table
        adj_records = [
            {
                "Feature": adj.feature_name,
                "Subject": str(adj.subject_value),
                "Comp": str(adj.comp_value),
                "Raw Difference": f"{adj.raw_difference:+.1f}",
                "Adjustment Rate": f"₹{adj.adjustment_rate:,.0f} / unit",
                "Applied Adjustment": f"₹{adj.adjustment_amount:+,.0f}",
                "Appraisal Rationale": adj.rationale,
            }
            for adj in selected_comp.adjustments
        ]
        if adj_records:
            st.markdown("##### Line-Item Appraisal Adjustments:")
            st.dataframe(adj_records, use_container_width=True)
