"""Market Conditions Analysis Engine."""

from typing import List, Optional, Tuple

import numpy as np

from src.core.enums import DataOrigin, MarketTrendDirection
from src.core.models import (
    SYNTHETIC_NOTICE_TEXT,
    MarketConditions,
    ProvenanceMetadata,
    SubmarketMetricPoint,
)


class MarketConditionsEngine:
    """Deterministic calculation of macro and submarket pricing, rental velocity, and yields."""

    @classmethod
    def calculate_metrics_from_points(
        cls,
        submarket_name: str,
        historical_points: List[SubmarketMetricPoint],
        time_horizon_months: int = 24,
        provenance: Optional[ProvenanceMetadata] = None,
    ) -> Optional[MarketConditions]:
        """Compute annualized growth, trailing momentum, average yields, and trend direction."""
        if not historical_points:
            return None

        # Sort points by period ascending
        sorted_points = sorted(historical_points, key=lambda p: p.period)
        points_to_use = sorted_points[-time_horizon_months:]
        num_periods = len(points_to_use)

        if num_periods < 2:
            first = points_to_use[0]
            annual_price_g = 0.0
            annual_rent_g = 0.0
            current_yield = round(first.gross_rental_yield_pct, 2)
            trend_dir = MarketTrendDirection.STABLE
            facts = f"Single data point available for {submarket_name} in {first.period}. Median sale PSF: ₹{first.median_sale_psf:,.2f}."
            interp = "Insufficient historical depth to evaluate macro trend direction."
            avg_inv = first.inventory_months
            avg_dom = float(first.avg_days_on_market)
            mom_6m_price = 0.0
            mom_6m_rent = 0.0
        else:
            first = points_to_use[0]
            last = points_to_use[-1]
            years_span = max(0.25, (num_periods - 1) / 12.0)

            # Annualized compound growth for sales PSF
            if first.median_sale_psf > 0 and last.median_sale_psf > 0:
                annual_price_g = round(float(((last.median_sale_psf / first.median_sale_psf) ** (1.0 / years_span) - 1.0) * 100), 2)
            else:
                annual_price_g = 0.0

            # Annualized compound growth for rental PSF
            if first.median_rent_psf > 0 and last.median_rent_psf > 0:
                annual_rent_g = round(float(((last.median_rent_psf / first.median_rent_psf) ** (1.0 / years_span) - 1.0) * 100), 2)
            else:
                annual_rent_g = 0.0

            # Current gross yield
            current_yield = round(last.gross_rental_yield_pct, 2)

            # Trailing 6-month momentum
            if num_periods >= 6:
                pt_6m = points_to_use[-6]
                mom_6m_price = round(float(((last.median_sale_psf - pt_6m.median_sale_psf) / pt_6m.median_sale_psf) * 100), 2)
                mom_6m_rent = round(float(((last.median_rent_psf - pt_6m.median_rent_psf) / pt_6m.median_rent_psf) * 100), 2)
            else:
                mom_6m_price = annual_price_g / 2.0
                mom_6m_rent = annual_rent_g / 2.0

            # Supply indicators
            avg_inv = round(float(np.mean([p.inventory_months for p in points_to_use])), 2)
            avg_dom = round(float(np.mean([p.avg_days_on_market for p in points_to_use])), 1)

            # Trend direction assignment
            if annual_price_g >= 2.5:
                trend_dir = MarketTrendDirection.APPRECIATING
            elif -1.0 <= annual_price_g < 2.5:
                trend_dir = MarketTrendDirection.STABLE
            elif -3.5 <= annual_price_g < -1.0:
                trend_dir = MarketTrendDirection.SOFTENING
            else:
                trend_dir = MarketTrendDirection.DECLINING

            # Factual summary (historical facts only)
            facts = (
                f"Historical facts ({first.period} to {last.period}): Median sale PSF transitioned from "
                f"₹{first.median_sale_psf:,.2f} to ₹{last.median_sale_psf:,.2f} ({annual_price_g:+.1f}% annualized). "
                f"Median rent moved from ₹{first.median_rent_psf:,.2f}/sqft to ₹{last.median_rent_psf:,.2f}/sqft "
                f"({annual_rent_g:+.1f}% annualized). Trailing average inventory: {avg_inv} months; "
                f"average DOM: {avg_dom:.0f} days. Current gross yield: {current_yield:.2f}%."
            )

            # Interpretive synthesis
            if trend_dir == MarketTrendDirection.APPRECIATING:
                interp = (
                    f"Submarket demonstrates positive pricing momentum ({annual_price_g:+.1f}%/yr) paired with "
                    f"tight supply ({avg_inv} mos inventory). Rental yields remain supportive of capital appreciation."
                )
            elif trend_dir == MarketTrendDirection.STABLE:
                interp = (
                    f"Balanced submarket equilibrium observed. Pricing changes are tracking closely with inflation; "
                    f"steady rental demand maintains yield stability."
                )
            elif trend_dir == MarketTrendDirection.SOFTENING:
                interp = (
                    f"Submarket displays mild softening with lengthening days on market. "
                    f"Conservative underwriting and defensive rental pricing are warranted."
                )
            else:
                interp = (
                    f"Submarket indicates contractionary pressures. High caution recommended on pricing expectations."
                )

        prov = provenance or ProvenanceMetadata(
            source="Synthetic Market Analysis Engine v1.0",
            origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
            notice=SYNTHETIC_NOTICE_TEXT,
            record_id=f"TREND-{submarket_name.upper().replace(' ', '-')}",
        )

        return MarketConditions(
            submarket_name=submarket_name,
            time_horizon_months=num_periods,
            historical_points=points_to_use,
            annual_price_growth_rate=annual_price_g,
            annual_rent_growth_rate=annual_rent_g,
            current_gross_yield_pct=current_yield,
            trend_direction=trend_dir,
            factual_summary=facts,
            agent_interpretation=interp,
            avg_inventory_months=avg_inv,
            avg_days_on_market=avg_dom,
            price_momentum_pct_6m=mom_6m_price,
            rent_momentum_pct_6m=mom_6m_rent,
            data_origin=prov.origin,
            provenance=prov,
        )
