"""Submarket macro conditions and historical trend view component."""

from typing import Optional

import streamlit as st

from src.core.models import MarketConditions
from src.ui.visualizations import plot_historical_psf_trend


def render_trends_view(conditions: Optional[MarketConditions]) -> None:
    """Render historical price trends, gross yields, and macro momentum metrics."""
    st.markdown("### 📈 Submarket Macro Conditions & Momentum")

    if not conditions:
        st.info("No submarket market conditions data available.")
        return

    # 1. Macro KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="Annual Price Growth",
            value=f"{conditions.annual_price_growth_rate:+.1f}% / yr",
            delta=f"{conditions.price_momentum_pct_6m:+.1f}% (6m)" if conditions.price_momentum_pct_6m is not None else None,
        )
    with c2:
        st.metric(
            label="Annual Rent Growth",
            value=f"{conditions.annual_rent_growth_rate:+.1f}% / yr",
            delta=f"{conditions.rent_momentum_pct_6m:+.1f}% (6m)" if conditions.rent_momentum_pct_6m is not None else None,
        )
    with c3:
        st.metric(
            label="Gross Rental Yield",
            value=f"{conditions.current_gross_yield_pct:.2f}%",
        )
    with c4:
        st.metric(
            label="Submarket Status",
            value=conditions.trend_direction.value,
            help=f"Avg Inventory: {conditions.avg_inventory_months or 'N/A'} mos, Avg DOM: {conditions.avg_days_on_market or 'N/A'} days",
        )

    # 2. Historical Trendline Chart
    fig = plot_historical_psf_trend(conditions)
    st.plotly_chart(fig, use_container_width=True)

    # 3. Strict Separation: Factual Market Facts vs Agent Interpretation
    col_fact, col_interp = st.columns(2)
    with col_fact:
        st.markdown("#### 📋 Factual Historical Record")
        st.info(f"**Verified Facts:** {conditions.factual_summary}")
        st.caption(f"Source: `{conditions.provenance.source}` · Origin: `{conditions.data_origin.value}`")

    with col_interp:
        st.markdown("#### 🤖 Agent Economic Interpretation")
        st.success(f"**Market Outlook:** {conditions.agent_interpretation}")
        st.caption("Classification: `AGENT INTERPRETATIONS` (Subject to human verification)")
