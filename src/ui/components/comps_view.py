"""Interactive Comparable Properties table and scatter visualization view component."""

from typing import List, Optional

import pandas as pd
import streamlit as st

from src.core.formatters import format_inr, format_psf
from src.core.models import ComparableProperty
from src.ui.visualizations import plot_comps_scatter


def render_comps_view(
    comparables: List[ComparableProperty],
    subject_sqft: float,
    subject_estimated_val: Optional[float] = None,
) -> None:
    """Render interactive comparables table and scatter visualization in INR."""
    st.markdown("### 🏘️ Comparable Properties (CMA)")

    if not comparables:
        st.info("No comparable properties to display.")
        return

    # 1. Comps Scatter Plot
    fig = plot_comps_scatter(comparables, subject_sqft, subject_estimated_val)
    st.plotly_chart(fig, use_container_width=True)

    # 2. Interactive Data Table
    table_data = []
    for c in comparables:
        table_data.append(
            {
                "Record ID": c.record.record_id,
                "Address": c.record.address,
                "Distance": f"{c.record.distance_km:.2f} km ({c.record.distance_miles:.2f} mi)",
                "Similarity": f"{c.similarity_score * 100:.1f}%",
                "Sale Price": format_inr(c.record.sale_price) if c.record.sale_price else "N/A",
                "Comp PSF": format_psf(c.record.price_per_sqft),
                "Built-up Area": f"{c.record.sqft:,.0f} sq ft",
                "Layout": f"{c.record.bhk_display} / {c.record.bathrooms:.0f} Bath",
                "Year Built": c.record.year_built,
                "Net Adjustment": f"₹{c.total_net_adjustment:+,.0f}",
                "Adjusted Price": format_inr(c.adjusted_price),
                "Adjusted PSF": format_psf(c.adjusted_price_psf),
                "Outlier?": "⚠️ OUTLIER" if c.is_outlier else "Normal",
                "Data Origin": c.record.data_origin.value,
            }
        )

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 3. Individual Selection Rationales
    with st.expander("📝 View Plain-Language Selection Rationales for Each Comparable"):
        for i, c in enumerate(comparables, 1):
            st.markdown(f"**{i}. {c.record.address} (Similarity: {c.similarity_score*100:.1f}%):**")
            st.markdown(f"> {c.selection_rationale}")
            st.caption(f"Source: `{c.record.provenance.source}` · Origin: `{c.record.data_origin.value}`")
            st.divider()
