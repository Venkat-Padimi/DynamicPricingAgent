"""Deterministic Property Valuation Engine."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.enums import ConfidenceLevel, PropertyType
from src.core.models import (
    LEGAL_DISCLAIMER_TEXT,
    CMAAnalysis,
    ComparableProperty,
    MarketConditions,
    PropertyProfile,
    RentRollSummary,
    ValuationComponentBreakdown,
    ValuationResult,
)
from src.core.scoring import ConfidenceScoringEngine


class DeterministicValuationEngine:
    """Mathematical multi-component property valuation engine outside the LLM."""

    DEFAULT_WEIGHTS = {
        "cma": 0.55,
        "trend": 0.15,
        "location": 0.10,
        "income": 0.20,
    }

    def __init__(self, component_weights: Optional[Dict[str, float]] = None):
        self.weights = component_weights or self.DEFAULT_WEIGHTS.copy()

    def calculate_valuation(
        self,
        subject: PropertyProfile,
        comparables: List[ComparableProperty],
        cma_analysis: CMAAnalysis,
        market_conditions: Optional[MarketConditions] = None,
        rent_roll_summary: Optional[RentRollSummary] = None,
    ) -> ValuationResult:
        """Compute transparent, deterministic valuation recommendation with full breakdown."""
        valid_comps = [c for c in comparables if not c.is_outlier]
        eval_comps = valid_comps if valid_comps else comparables

        key_drivers: List[str] = []
        limitations: List[str] = []

        # 1. CMA Sales Component
        if eval_comps and cma_analysis.adjusted_median_price > 0:
            # Weighted average by similarity score
            sim_weights = np.array([c.similarity_score for c in eval_comps])
            adj_prices = np.array([c.adjusted_price for c in eval_comps])
            cma_val = float(np.sum(sim_weights * adj_prices) / np.sum(sim_weights))
            key_drivers.append(
                f"CMA weighted baseline of ${cma_val:,.0f} derived from {len(eval_comps)} "
                f"comparable sales (median ${cma_analysis.adjusted_median_price:,.0f})"
            )
        else:
            # Fallback when zero comps
            fallback_psf = market_conditions.historical_points[-1].median_sale_psf if market_conditions and market_conditions.historical_points else 450.0
            cma_val = fallback_psf * subject.sqft
            limitations.append("Insufficient sales comparables; valuation defaulted to submarket average PSF.")

        # 2. Market Trend Component
        if market_conditions and market_conditions.price_momentum_pct_6m is not None:
            mom_pct = market_conditions.price_momentum_pct_6m / 100.0
            trend_val = cma_val * (1.0 + mom_pct)
            key_drivers.append(
                f"Submarket 6-month price momentum ({market_conditions.price_momentum_pct_6m:+.1f}%) "
                f"contributed a trend valuation component of ${trend_val:,.0f}"
            )
        else:
            trend_val = cma_val
            limitations.append("Submarket price momentum data unavailable; trend factor neutralized.")

        # 3. Location Component
        if eval_comps:
            avg_dist = float(np.mean([c.record.distance_miles for c in eval_comps]))
            # Distance discount if comps are far
            loc_factor = 1.0 - min(0.05, max(0.0, (avg_dist - 0.5) * 0.02))
            loc_val = cma_val * loc_factor
            if avg_dist <= 0.4:
                key_drivers.append(f"Tight comparable proximity (avg {avg_dist:.2f} mi) reinforces micro-location stability.")
        else:
            loc_val = cma_val

        # 4. Income Capitalization Component
        income_val: Optional[float] = None
        has_income = False

        annual_rent = 0.0
        if rent_roll_summary and rent_roll_summary.current_in_place_monthly_rent > 0:
            annual_rent = rent_roll_summary.current_in_place_monthly_rent * 12.0
        elif subject.current_rent and subject.current_rent > 0:
            annual_rent = subject.current_rent * 12.0

        if annual_rent > 0 and market_conditions and market_conditions.current_gross_yield_pct > 0:
            cap_yield = market_conditions.current_gross_yield_pct / 100.0
            income_val = round(annual_rent / cap_yield, 2)
            has_income = True
            key_drivers.append(
                f"Income capitalization value of ${income_val:,.0f} based on ${annual_rent:,.0f} "
                f"annual gross rent capitalized at {market_conditions.current_gross_yield_pct:.2f}% gross yield"
            )
        else:
            limitations.append("Income capitalization not applicable (subject property is not actively leased or cap yield missing).")

        # Dynamic weight renormalization
        active_weights = self.weights.copy()
        if not has_income:
            active_weights["income"] = 0.0
        total_w = sum(active_weights.values())
        norm_w = {k: v / total_w for k, v in active_weights.items()}

        # Weighted estimate
        raw_estimate = (
            norm_w["cma"] * cma_val
            + norm_w["trend"] * trend_val
            + norm_w["location"] * loc_val
            + (norm_w["income"] * income_val if has_income and income_val else 0.0)
        )

        # 5. Confidence scoring & Data Quality Adjustment
        conf_level, conf_score, conf_breakdown = ConfidenceScoringEngine.calculate_confidence(
            comparables=comparables,
            market_conditions=market_conditions,
            rent_roll_summary=rent_roll_summary,
            has_complete_specs=True,
        )

        # Haircut penalty if low confidence
        if conf_level == ConfidenceLevel.LOW:
            quality_adj = -0.03 * raw_estimate
            limitations.append("3.0% data quality haircut applied due to low confidence scoring.")
        else:
            quality_adj = 0.0

        final_val = max(50000.0, round(raw_estimate + quality_adj, -2))
        val_psf = round(final_val / subject.sqft, 2)

        # Valuation Range calculation
        uncertainty_margin = max(0.04, 0.14 * (1.0 - conf_score / 100.0))
        if eval_comps and cma_analysis.adjusted_price_low > 0:
            range_low = min(cma_analysis.adjusted_price_low, final_val * (1.0 - uncertainty_margin))
            range_high = max(cma_analysis.adjusted_price_high, final_val * (1.0 + uncertainty_margin))
        else:
            range_low = final_val * (1.0 - uncertainty_margin)
            range_high = final_val * (1.0 + uncertainty_margin)

        range_low = round(range_low, -2)
        range_high = round(range_high, -2)

        breakdown = ValuationComponentBreakdown(
            cma_sales_component=round(cma_val, 2),
            cma_weight=round(norm_w["cma"], 3),
            property_feature_adjustment=0.0,
            market_trend_component=round(trend_val, 2),
            market_trend_weight=round(norm_w["trend"], 3),
            location_component=round(loc_val, 2),
            location_weight=round(norm_w["location"], 3),
            income_capitalization_component=round(income_val, 2) if income_val else None,
            income_weight=round(norm_w["income"], 3),
            data_quality_adjustment=round(quality_adj, 2),
        )

        methodology = (
            f"Multi-component deterministic valuation combining CMA adjusted sales ({norm_w['cma']*100:.0f}%), "
            f"submarket momentum trend ({norm_w['trend']*100:.0f}%), micro-location factors ({norm_w['location']*100:.0f}%), "
            f"and income capitalization ({norm_w['income']*100:.0f}%)."
        )

        return ValuationResult(
            property_id=subject.property_id,
            estimated_value=final_val,
            valuation_range_low=range_low,
            valuation_range_high=range_high,
            valuation_psf=val_psf,
            confidence_level=conf_level,
            confidence_score=conf_score,
            breakdown=breakdown,
            key_drivers=key_drivers,
            limitations=limitations,
            methodology=methodology,
            legal_disclaimer=LEGAL_DISCLAIMER_TEXT,
            timestamp=datetime.now(timezone.utc),
        )
