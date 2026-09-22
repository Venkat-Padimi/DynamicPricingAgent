"""Deterministic Dynamic Rental Pricing Engine."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.enums import ConfidenceLevel, PropertyCondition
from src.core.models import (
    LEGAL_DISCLAIMER_TEXT,
    MarketConditions,
    MarketRecord,
    PropertyProfile,
    RentalPricingBreakdown,
    RentalPricingResult,
    RentRollSummary,
)
from src.core.scoring import ConfidenceScoringEngine


class DeterministicPricingEngine:
    """Mathematical rental pricing engine calculating recommended rent ranges and gap analysis."""

    @classmethod
    def calculate_rental_pricing(
        cls,
        subject: PropertyProfile,
        rental_records: List[MarketRecord],
        market_conditions: Optional[MarketConditions] = None,
        rent_roll_summary: Optional[RentRollSummary] = None,
    ) -> RentalPricingResult:
        """Compute transparent recommended rental price range and gap metrics."""
        pricing_drivers: List[str] = []

        # 1. Base Market Rent from Comps
        if rental_records:
            # Filter valid rental transactions with positive monthly rent
            valid_rents = [r for r in rental_records if r.monthly_rent and r.monthly_rent > 0]
            if valid_rents:
                # Compute rent per sqft
                rent_psfs = [r.rent_per_sqft for r in valid_rents if r.rent_per_sqft > 0]
                median_rent_psf = float(np.median(rent_psfs)) if rent_psfs else 2.65
                base_comp_rent = round(median_rent_psf * subject.sqft, 2)
                pricing_drivers.append(
                    f"Market rental comps established a baseline of ${median_rent_psf:.2f}/sqft "
                    f"(${base_comp_rent:,.0f}/mo) across {len(valid_rents)} local rental records."
                )
            else:
                base_comp_rent = round(2.65 * subject.sqft, 2)
        elif market_conditions and market_conditions.historical_points:
            last_pt = market_conditions.historical_points[-1]
            base_comp_rent = round(last_pt.median_rent_psf * subject.sqft, 2)
            pricing_drivers.append(
                f"Submarket median rental PSF (${last_pt.median_rent_psf:.2f}/sqft) used as baseline (${base_comp_rent:,.0f}/mo)."
            )
        else:
            base_comp_rent = round(2.60 * subject.sqft, 2)
            pricing_drivers.append(f"Fallback rental baseline applied at $2.60/sqft (${base_comp_rent:,.0f}/mo).")

        # 2. Property Condition & Amenity Premium
        condition_factors = {
            PropertyCondition.LUXURY_RENOVATED: 0.06,
            PropertyCondition.EXCELLENT: 0.03,
            PropertyCondition.GOOD: 0.0,
            PropertyCondition.FAIR: -0.05,
            PropertyCondition.POOR: -0.10,
        }
        cond_pct = condition_factors.get(subject.condition, 0.0)

        amenities_count = len(subject.amenities)
        amenity_pct = min(0.04, amenities_count * 0.01)
        total_feature_pct = cond_pct + amenity_pct
        feature_adj = round(base_comp_rent * total_feature_pct, 2)

        if total_feature_pct != 0:
            pricing_drivers.append(
                f"Property condition ({subject.condition.value}) and {amenities_count} amenities contributed "
                f"a net adjustment of {total_feature_pct * 100:+.1f}% (${feature_adj:+,.0f}/mo)."
            )

        # 3. Occupancy Leverage Adjustment
        occupancy_adj = 0.0
        if rent_roll_summary and rent_roll_summary.total_units > 0:
            occ_rate = rent_roll_summary.physical_occupancy_rate
            if occ_rate >= 0.90:
                occ_adj_pct = 0.025
                pricing_drivers.append(f"High property occupancy ({occ_rate * 100:.1f}%) provides +2.5% pricing leverage.")
            elif occ_rate < 0.75:
                occ_adj_pct = -0.03
                pricing_drivers.append(f"Below-target occupancy ({occ_rate * 100:.1f}%) necessitates a -3.0% lease-up incentive.")
            else:
                occ_adj_pct = 0.0
            occupancy_adj = round(base_comp_rent * occ_adj_pct, 2)

        # 4. Lease Expiration Timing Adjustment
        timing_adj = 0.0
        if rent_roll_summary and rent_roll_summary.cliff_risk_level == "HIGH":
            timing_adj = round(-0.02 * base_comp_rent, 2)
            pricing_drivers.append("High 90-day lease expiration cliff applies a -2.0% defensive pricing discount to encourage early renewals.")

        # 5. Submarket Momentum Adjustment
        momentum_adj = 0.0
        if market_conditions and market_conditions.rent_momentum_pct_6m is not None:
            mom_pct = market_conditions.rent_momentum_pct_6m / 100.0
            momentum_adj = round(base_comp_rent * (mom_pct * 0.5), 2)
            if abs(momentum_adj) > 10.0:
                pricing_drivers.append(
                    f"Submarket 6-month rent momentum ({market_conditions.rent_momentum_pct_6m:+.1f}%) "
                    f"adjusted recommendation by ${momentum_adj:+,.0f}/mo."
                )

        # Calculate Midpoint & Range
        raw_market_rent = base_comp_rent + feature_adj + occupancy_adj + timing_adj + momentum_adj
        midpoint = max(500.0, round(raw_market_rent / 25.0) * 25.0)
        floor_rent = round(midpoint * 0.95 / 25.0) * 25.0
        ceiling_rent = round(midpoint * 1.06 / 25.0) * 25.0

        # In-place Rent & Gap Analysis
        current_rent = None
        if rent_roll_summary and rent_roll_summary.avg_rent_per_unit > 0:
            current_rent = rent_roll_summary.avg_rent_per_unit
        elif subject.current_rent and subject.current_rent > 0:
            current_rent = subject.current_rent

        rent_gap_amt = None
        rent_gap_pct = None
        if current_rent and current_rent > 0:
            rent_gap_amt = round(midpoint - current_rent, 2)
            rent_gap_pct = round((rent_gap_amt / current_rent) * 100, 2)
            pricing_drivers.append(
                f"Rent gap analysis: in-place rent of ${current_rent:,.0f}/mo is "
                f"${abs(rent_gap_amt):,.0f} ({abs(rent_gap_pct):.1f}%) {'below' if rent_gap_amt > 0 else 'above'} "
                f"recommended market midpoint (${midpoint:,.0f}/mo)."
            )

        # Confidence determination
        # Format fake/empty comparables list to score completeness
        conf_level, conf_score, _ = ConfidenceScoringEngine.calculate_confidence(
            comparables=[],
            market_conditions=market_conditions,
            rent_roll_summary=rent_roll_summary,
            has_complete_specs=True,
        )
        # If we have 3+ rental records, boost confidence
        if len(rental_records) >= 3:
            conf_score = min(100.0, conf_score + 30.0)
            if conf_score >= 75.0:
                conf_level = ConfidenceLevel.HIGH
            elif conf_score >= 50.0:
                conf_level = ConfidenceLevel.MEDIUM

        breakdown = RentalPricingBreakdown(
            base_market_comp_rent=base_comp_rent,
            occupancy_leverage_adjustment=occupancy_adj,
            lease_expiration_timing_adjustment=timing_adj,
            property_condition_premium=feature_adj,
            submarket_momentum_adjustment=momentum_adj,
        )

        seasonal_str = "Standard seasonal leasing rate environment."
        if market_conditions and market_conditions.trend_direction.value == "APPRECIATING":
            seasonal_str = "High absorption environment with favorable landlord negotiation posture."

        return RentalPricingResult(
            property_id=subject.property_id,
            current_in_place_rent=current_rent,
            estimated_market_rent=midpoint,
            recommended_rent_range_low=floor_rent,
            recommended_rent_range_high=ceiling_rent,
            recommended_midpoint=midpoint,
            rent_gap_amount=rent_gap_amt,
            rent_gap_percentage=rent_gap_pct,
            confidence_level=conf_level,
            confidence_score=round(conf_score, 1),
            breakdown=breakdown,
            pricing_drivers=pricing_drivers,
            seasonal_factors=seasonal_str,
            disclaimer=LEGAL_DISCLAIMER_TEXT,
            timestamp=datetime.now(timezone.utc),
        )
