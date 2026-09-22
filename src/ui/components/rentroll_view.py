"""Operational lease schedule and rent-roll dashboard component."""

from typing import List, Optional

import pandas as pd
import streamlit as st

from src.core.models import RentRollSummary, RentRollUnit
from src.ui.visualizations import plot_lease_cliff_ladder


def render_rentroll_view(
    summary: Optional[RentRollSummary],
    units: List[RentRollUnit],
) -> None:
    """Render operational rent roll, occupancy rates, and expiration cliff ladder."""
    st.markdown("### 🏢 Operational Rent Roll & Lease Cliff Analysis")

    if not summary or not units:
        st.info("No active unit-level rent roll on file for this property. Asset is treated as unleased / single-tenant.")
        return

    # 1. Operational Occupancy KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="Physical Occupancy",
            value=f"{summary.physical_occupancy_rate * 100:.1f}%",
            help=f"{summary.occupied_units} of {summary.total_units} units actively occupied.",
        )
    with c2:
        st.metric(
            label="Economic Occupancy",
            value=f"{summary.economic_occupancy_rate * 100:.1f}%",
            help="Collected in-place rent divided by gross potential market rent.",
        )
    with c3:
        st.metric(
            label="In-Place Monthly Rent",
            value=f"${summary.current_in_place_monthly_rent:,.0f} / mo",
            help=f"Gross Annual: ${summary.gross_annual_in_place_rent:,.0f} / yr",
        )
    with c4:
        st.metric(
            label="90-Day Cliff Risk",
            value=f"{summary.cliff_risk_level} ({summary.lease_turnover_exposure_pct:.0f}%)",
            delta=f"-${summary.expiring_rent_within_90_days:,.0f}/mo at risk" if summary.expiring_rent_within_90_days > 0 else None,
            delta_color="inverse",
            help="Total percentage of building rent rolling over within the next 90 days.",
        )

    # 2. Expiration Cliff Ladder Plot
    fig = plot_lease_cliff_ladder(summary)
    st.plotly_chart(fig, use_container_width=True)

    # 3. Anonymized Unit-Level Rent Roll (Zero PII Guarantee)
    st.markdown("#### 🔒 Anonymized Unit Schedule (Strictly Zero PII)")
    unit_rows = [
        {
            "Unit #": u.unit_number,
            "Bed / Bath": f"{u.bedrooms}B / {u.bathrooms:.0f}Ba",
            "Area": f"{u.sqft:,.0f} sqft",
            "In-Place Rent": f"${u.current_rent:,.0f} / mo" if u.current_rent > 0 else "$0 (Vacant)",
            "Rent PSF": f"${u.in_place_psf:.2f}",
            "Lease Expiration": u.lease_end,
            "Days to Expire": f"{u.days_until_expiration} days",
            "Lease Status": u.lease_status.value,
            "Tenant Identifier": u.tenant_pseudonym,  # Anonymized pseudonym
        }
        for u in units
    ]
    df = pd.DataFrame(unit_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("🔒 **Privacy Guarantee:** All tenant personal identifiers are pseudonymized. No tenant names, emails, or personal data are stored or exposed.")
