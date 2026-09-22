"""Plotly visualization builders for institutional real estate analytics."""

from typing import List, Optional

import numpy as np
import plotly.graph_objects as go

from src.core.models import ComparableProperty, MarketConditions, RentRollSummary

CHART_THEME = {
    "paper_bgcolor": "#1e293b",
    "plot_bgcolor": "#0f172a",
    "font": {"color": "#f8fafc", "family": "Inter, system-ui, sans-serif"},
    "gridcolor": "#334155",
}


def plot_comps_scatter(
    comparables: List[ComparableProperty],
    subject_sqft: float,
    subject_estimated_val: Optional[float] = None,
) -> go.Figure:
    """Generate scatter plot comparing subject property to comparables by size and price."""
    fig = go.Figure()

    if not comparables:
        fig.add_annotation(
            text="No comparable property data available to plot.",
            showarrow=False,
            font={"size": 14, "color": "#94a3b8"},
        )
        fig.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font=CHART_THEME["font"],
        )
        return fig

    # 1. Non-outlier comparables
    valid_comps = [c for c in comparables if not c.is_outlier]
    if valid_comps:
        x_vals = [c.record.sqft for c in valid_comps]
        y_vals = [c.record.sale_price or (c.record.monthly_rent * 180 if c.record.monthly_rent else 0) for c in valid_comps]
        hover_texts = [
            f"<b>{c.record.address}</b><br>"
            f"Distance: {c.record.distance_miles:.2f} mi<br>"
            f"Similarity: {c.similarity_score * 100:.1f}%<br>"
            f"Sale Price: ${c.record.sale_price or 0:,.0f}<br>"
            f"Adjusted Price: ${c.adjusted_price:,.0f}<br>"
            f"Source: {c.record.data_origin.value}"
            for c in valid_comps
        ]
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers+text",
                marker=dict(
                    size=14,
                    color=[c.similarity_score for c in valid_comps],
                    colorscale="Blues",
                    showscale=True,
                    colorbar=dict(title="Similarity", thickness=12),
                    line=dict(width=1.5, color="#38bdf8"),
                ),
                text=[f"{c.similarity_score*100:.0f}%" for c in valid_comps],
                textposition="top center",
                hovertext=hover_texts,
                hoverinfo="text",
                name="Comparables",
            )
        )

    # 2. Statistical outliers
    outliers = [c for c in comparables if c.is_outlier]
    if outliers:
        fig.add_trace(
            go.Scatter(
                x=[c.record.sqft for c in outliers],
                y=[c.record.sale_price or 0 for c in outliers],
                mode="markers",
                marker=dict(size=14, color="#ef4444", symbol="x", line=dict(width=2, color="#fca5a5")),
                hovertext=[f"<b>OUTLIER: {c.record.address}</b><br>Sale Price: ${c.record.sale_price or 0:,.0f}" for c in outliers],
                hoverinfo="text",
                name="Statistical Outliers",
            )
        )

    # 3. Subject property marker
    if subject_estimated_val and subject_estimated_val > 0:
        fig.add_trace(
            go.Scatter(
                x=[subject_sqft],
                y=[subject_estimated_val],
                mode="markers+text",
                marker=dict(size=18, color="#f59e0b", symbol="star", line=dict(width=2, color="#fbbf24")),
                text=["Subject"],
                textposition="bottom center",
                hovertext=f"<b>SUBJECT PROPERTY</b><br>Area: {subject_sqft:,.0f} sqft<br>Estimated Value: ${subject_estimated_val:,.0f}",
                hoverinfo="text",
                name="Subject Property",
            )
        )

    fig.update_layout(
        title="<b>Comparable Sales Price vs Living Area (Sq Ft)</b>",
        xaxis=dict(title="Living Area (Sq Ft)", gridcolor=CHART_THEME["gridcolor"]),
        yaxis=dict(title="Price ($)", tickprefix="$", tickformat=",.0f", gridcolor=CHART_THEME["gridcolor"]),
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=CHART_THEME["font"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def plot_cma_waterfall(comp: ComparableProperty) -> go.Figure:
    """Generate Waterfall chart demonstrating step-by-step appraisal adjustments for a comparable."""
    fig = go.Figure()

    base_price = comp.record.sale_price or 0.0
    measure = ["absolute"]
    x = ["Base Sale Price"]
    y = [base_price]
    text = [f"${base_price:,.0f}"]

    for adj in comp.adjustments:
        if abs(adj.adjustment_amount) > 0:
            measure.append("relative")
            x.append(adj.feature_name)
            y.append(adj.adjustment_amount)
            text.append(f"{adj.adjustment_amount:+,.0f}")

    measure.append("total")
    x.append("Adjusted Price")
    y.append(comp.adjusted_price)
    text.append(f"${comp.adjusted_price:,.0f}")

    fig.add_trace(
        go.Waterfall(
            name="CMA Adjustments",
            orientation="v",
            measure=measure,
            x=x,
            textposition="outside",
            text=text,
            y=y,
            connector={"line": {"color": "#64748b"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#10b981"}},
            totals={"marker": {"color": "#3b82f6"}},
        )
    )

    fig.update_layout(
        title=f"<b>Feature Adjustments: {comp.record.address}</b>",
        yaxis=dict(title="Dollar Impact ($)", tickprefix="$", tickformat=",.0f", gridcolor=CHART_THEME["gridcolor"]),
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=CHART_THEME["font"],
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def plot_historical_psf_trend(market_conditions: Optional[MarketConditions]) -> go.Figure:
    """Generate multi-line trend of historical sales PSF and rental PSF over 24 months."""
    fig = go.Figure()

    if not market_conditions or not market_conditions.historical_points:
        fig.add_annotation(
            text="Historical submarket trend data unavailable.",
            showarrow=False,
            font={"size": 14, "color": "#94a3b8"},
        )
        fig.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font=CHART_THEME["font"],
        )
        return fig

    pts = market_conditions.historical_points
    periods = [p.period for p in pts]
    sale_psf = [p.median_sale_psf for p in pts]
    rent_psf = [p.median_rent_psf for p in pts]

    fig.add_trace(
        go.Scatter(
            x=periods,
            y=sale_psf,
            name="Sales PSF ($)",
            mode="lines+markers",
            line=dict(color="#38bdf8", width=2.5),
            marker=dict(size=6),
            yaxis="y1",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=periods,
            y=rent_psf,
            name="Rental PSF ($/mo)",
            mode="lines+markers",
            line=dict(color="#34d399", width=2.5, dash="dash"),
            marker=dict(size=6),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title=f"<b>Historical Price & Rent Trends: {market_conditions.submarket_name}</b>",
        xaxis=dict(title="Period (YYYY-MM)", gridcolor=CHART_THEME["gridcolor"]),
        yaxis=dict(
            title=dict(text="Sales PSF ($)", font=dict(color="#38bdf8")),
            tickprefix="$",
            gridcolor=CHART_THEME["gridcolor"],
            tickfont=dict(color="#38bdf8"),
        ),
        yaxis2=dict(
            title=dict(text="Rental PSF ($)", font=dict(color="#34d399")),
            tickprefix="$",
            overlaying="y",
            side="right",
            gridcolor="#1e293b",
            tickfont=dict(color="#34d399"),
        ),
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=CHART_THEME["font"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def plot_lease_cliff_ladder(rent_roll_summary: Optional[RentRollSummary]) -> go.Figure:
    """Generate bar chart displaying the 30/60/90-day lease expiration cliff ladder."""
    fig = go.Figure()

    if not rent_roll_summary or rent_roll_summary.total_units == 0:
        fig.add_annotation(
            text="No active lease rent-roll data available.",
            showarrow=False,
            font={"size": 14, "color": "#94a3b8"},
        )
        fig.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font=CHART_THEME["font"],
        )
        return fig

    categories = ["0–30 Days", "31–60 Days", "61–90 Days", ">90 Days / Stable"]
    unit_counts = [
        rent_roll_summary.expiring_within_30_days,
        rent_roll_summary.expiring_within_60_days,
        rent_roll_summary.expiring_within_90_days,
        rent_roll_summary.expiring_beyond_90_days,
    ]
    colors = ["#ef4444", "#f97316", "#eab308", "#10b981"]

    fig.add_trace(
        go.Bar(
            x=categories,
            y=unit_counts,
            text=[f"{cnt} unit(s)" for cnt in unit_counts],
            textposition="auto",
            marker=dict(color=colors, line=dict(width=1, color="#334155")),
            hovertext=[
                f"<b>{cat}</b>: {cnt} unit(s) facing rollover"
                for cat, cnt in zip(categories, unit_counts)
            ],
            hoverinfo="text",
        )
    )

    fig.update_layout(
        title=f"<b>Lease Expiration Cliff Schedule (Risk Level: {rent_roll_summary.cliff_risk_level})</b>",
        xaxis=dict(title="Expiration Horizon", gridcolor=CHART_THEME["gridcolor"]),
        yaxis=dict(title="Unit Count", gridcolor=CHART_THEME["gridcolor"], dtick=1),
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font=CHART_THEME["font"],
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig
