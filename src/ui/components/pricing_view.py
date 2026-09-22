"""Dynamic rental pricing dashboard component."""

from typing import Optional

import streamlit as st

from src.core.formatters import format_inr, format_rent
from src.core.models import RentalPricingResult


def render_pricing_view(pricing: Optional[RentalPricingResult]) -> None:
    """Render dynamic rental pricing recommendation cards, range, and rent gap analysis in INR."""
    if not pricing:
        st.warning("⚠️ No rental pricing estimate available.")
        return

    st.markdown("### 🏷️ Dynamic Rental Pricing Recommendation")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            label="Recommended Market Rent",
            value=format_rent(pricing.recommended_midpoint),
            help="Deterministic rental recommendation calibrated against local comps, occupancy, and lease cliff factors.",
        )

    with c2:
        st.metric(
            label="Recommended Range",
            value=f"{format_inr(pricing.recommended_rent_range_low)} – {format_inr(pricing.recommended_rent_range_high)} / mo",
            help="Floor (defensive lease-up) to Ceiling (peak premium demand).",
        )

    with c3:
        in_place_str = format_rent(pricing.current_in_place_rent) if pricing.current_in_place_rent else "Vacant / Unleased"
        st.metric(
            label="In-Place Current Rent",
            value=in_place_str,
        )

    with c4:
        if pricing.rent_gap_amount is not None:
            gap_label = f"{pricing.rent_gap_percentage:+.1f}% ({format_inr(pricing.rent_gap_amount)})"
            st.metric(
                label="Potential Rent Gap",
                value=gap_label,
                delta=f"₹{pricing.rent_gap_amount:+,.0f}",
                help="Variance between recommended market midpoint and in-place collected rent.",
            )
        else:
            st.metric(label="Potential Rent Gap", value="N/A (No in-place rent)")

    with st.expander("🔍 View Rental Pricing Formula Drivers", expanded=False):
        b = pricing.breakdown
        st.markdown(f"- **Base Market Rental Comps:** `{format_rent(b.base_market_comp_rent)}`")
        st.markdown(f"- **Condition & Amenity Premium:** `₹{b.property_condition_premium:+,.2f} / mo`")
        st.markdown(f"- **Occupancy Leverage Adjustment:** `₹{b.occupancy_leverage_adjustment:+,.2f} / mo`")
        st.markdown(f"- **Lease Expiration Timing Adjustment:** `₹{b.lease_expiration_timing_adjustment:+,.2f} / mo`")
        st.markdown(f"- **Submarket Momentum Adjustment:** `₹{b.submarket_momentum_adjustment:+,.2f} / mo`")

        if pricing.pricing_drivers:
            st.markdown("##### Specific Pricing Drivers:")
            for d in pricing.pricing_drivers:
                st.markdown(f"• {d}")

    st.caption("🔒 **Notice:** AI pricing recommendations are advisory and must be reviewed and approved prior to listing.")
