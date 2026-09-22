"""Interactive Comparable Properties table and scatter visualization view component."""

from typing import List, Optional

import pandas as pd
import streamlit as st

from src.core.models import ComparableProperty
from src.ui.visualizations import plot_comps_scatter


def render_comps_view(
    comparables: List[ComparableProperty],
    subject_sqft: float,
    subject_estimated_val: Optional[float] = None,
) -> None:
    """Render interactive comparables table and scatter visualization."""
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
                "Distance (mi)": f"{c.record.distance_miles:.2f}",
                "Similarity": f"{c.similarity_score * 100:.1f}%",
                "Sale Price": f"${c.record.sale_price:,.0f}" if c.record.sale_price else "N/A",
                "Comp PSF": f"${c.record.price_per_sqft:,.0f}",
                "Living Area": f"{c.record.sqft:,.0f} sqft",
                "Bed / Bath": f"{c.record.bedrooms}B / {c.record.bathrooms:.0f}Ba",
                "Year Built": c.record.year_built,
                "Net Adjustment": f"${c.total_net_adjustment:+,.0f}",
                "Adjusted Price": f"${c.adjusted_price:,.0f}",
                "Adjusted PSF": f"${c.adjusted_price_psf:,.0f}",
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
