"""Comparable Property Selection and Comparative Market Analysis (CMA) Engine."""

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.enums import PropertyCondition, PropertyType
from src.core.models import (
    CMAAnalysis,
    ComparableProperty,
    FeatureAdjustment,
    MarketRecord,
    PropertyProfile,
)

CONDITION_RANKS: Dict[PropertyCondition, int] = {
    PropertyCondition.POOR: 1,
    PropertyCondition.FAIR: 2,
    PropertyCondition.GOOD: 3,
    PropertyCondition.EXCELLENT: 4,
    PropertyCondition.LUXURY_RENOVATED: 5,
}


class SimilarityCalculator:
    """Multi-attribute similarity scoring engine between subject property and market comparables."""

    DEFAULT_WEIGHTS = {
        "distance": 0.25,
        "sqft": 0.25,
        "beds_baths": 0.15,
        "age": 0.10,
        "condition": 0.15,
        "amenities": 0.10,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None, max_distance_miles: float = 3.0):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.max_distance_miles = max_distance_miles

        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def calculate_similarity(self, subject: PropertyProfile, comp: MarketRecord) -> float:
        """Compute composite similarity index between 0.0 and 1.0."""
        # 1. Distance similarity
        dist_sim = max(0.0, 1.0 - (comp.distance_miles / max(self.max_distance_miles, 0.1)))

        # 2. Sqft similarity (proportional difference)
        sqft_diff = abs(subject.sqft - comp.sqft)
        sqft_sim = max(0.0, 1.0 - (sqft_diff / max(subject.sqft, 1.0)))

        # 3. Bedroom and bathroom match
        bed_diff = abs(subject.bedrooms - comp.bedrooms)
        bath_diff = abs(subject.bathrooms - comp.bathrooms)
        bed_bath_sim = max(0.0, 1.0 - (0.4 * bed_diff + 0.2 * bath_diff))

        # 4. Age similarity
        subject_age = subject.age_years
        comp_age = max(0, 2026 - comp.year_built)
        age_diff = abs(subject_age - comp_age)
        age_sim = max(0.0, 1.0 - (age_diff / 40.0))

        # 5. Condition similarity
        subj_cond_rank = CONDITION_RANKS.get(subject.condition, 3)
        comp_cond_rank = CONDITION_RANKS.get(comp.condition, 3)
        cond_diff = abs(subj_cond_rank - comp_cond_rank)
        cond_sim = max(0.0, 1.0 - (cond_diff / 4.0))

        # 6. Amenities similarity (Jaccard index)
        subj_amenities = set(a.lower().strip() for a in subject.amenities)
        comp_amenities = set(a.lower().strip() for a in comp.amenities)
        if not subj_amenities and not comp_amenities:
            amenities_sim = 1.0
        elif not subj_amenities or not comp_amenities:
            amenities_sim = 0.5
        else:
            intersection = len(subj_amenities & comp_amenities)
            union = len(subj_amenities | comp_amenities)
            amenities_sim = intersection / union if union > 0 else 1.0

        # Weighted composite
        raw_score = (
            self.weights["distance"] * dist_sim
            + self.weights["sqft"] * sqft_sim
            + self.weights["beds_baths"] * bed_bath_sim
            + self.weights["age"] * age_sim
            + self.weights["condition"] * cond_sim
            + self.weights["amenities"] * amenities_sim
        )

        # Property type bonus/penalty
        type_multiplier = 1.0 if subject.property_type == comp.property_type else 0.70

        return round(float(np.clip(raw_score * type_multiplier, 0.0, 1.0)), 4)


class AdjustmentEngine:
    """Performs appraisal-standard feature adjustments on comparable properties.

    Adjustment Rule: Adjust the COMPARABLE to the SUBJECT.
    If subject is superior, comp price is adjusted UP (+).
    If subject is inferior, comp price is adjusted DOWN (-).
    """

    SQFT_ADJUSTMENT_RATE = 150.0  # $ per sqft
    BEDROOM_ADJUSTMENT_RATE = 15000.0  # $ per bedroom
    BATHROOM_ADJUSTMENT_RATE = 10000.0  # $ per full bathroom
    AGE_ADJUSTMENT_RATE = 1500.0  # $ per year of age difference
    CONDITION_ADJUSTMENT_RATE = 12000.0  # $ per condition rank step
    PARKING_ADJUSTMENT_RATE = 8000.0  # $ per parking space
    AMENITY_ITEM_VALUE = 8000.0  # $ per key amenity difference

    @classmethod
    def calculate_adjustments(
        cls, subject: PropertyProfile, comp: MarketRecord
    ) -> Tuple[List[FeatureAdjustment], float, float]:
        """Compute line-item adjustments and adjusted price for a comparable."""
        adjustments: List[FeatureAdjustment] = []

        # 1. Square footage adjustment
        sqft_diff = subject.sqft - comp.sqft
        sqft_adj = sqft_diff * cls.SQFT_ADJUSTMENT_RATE
        adjustments.append(
            FeatureAdjustment(
                feature_name="Square Footage",
                subject_value=f"{subject.sqft:,.0f} sqft",
                comp_value=f"{comp.sqft:,.0f} sqft",
                raw_difference=sqft_diff,
                adjustment_rate=cls.SQFT_ADJUSTMENT_RATE,
                adjustment_amount=round(sqft_adj, 2),
                rationale=(
                    f"Subject is {abs(sqft_diff):.0f} sqft {'larger' if sqft_diff > 0 else 'smaller'} than comp"
                    if sqft_diff != 0
                    else "Identical square footage"
                ),
            )
        )

        # 2. Bedrooms adjustment
        bed_diff = subject.bedrooms - comp.bedrooms
        bed_adj = bed_diff * cls.BEDROOM_ADJUSTMENT_RATE
        if bed_diff != 0:
            adjustments.append(
                FeatureAdjustment(
                    feature_name="Bedrooms",
                    subject_value=subject.bedrooms,
                    comp_value=comp.bedrooms,
                    raw_difference=float(bed_diff),
                    adjustment_rate=cls.BEDROOM_ADJUSTMENT_RATE,
                    adjustment_amount=round(bed_adj, 2),
                    rationale=f"Subject has {abs(bed_diff)} {'more' if bed_diff > 0 else 'fewer'} bedroom(s)",
                )
            )

        # 3. Bathrooms adjustment
        bath_diff = subject.bathrooms - comp.bathrooms
        bath_adj = bath_diff * cls.BATHROOM_ADJUSTMENT_RATE
        if bath_diff != 0:
            adjustments.append(
                FeatureAdjustment(
                    feature_name="Bathrooms",
                    subject_value=subject.bathrooms,
                    comp_value=comp.bathrooms,
                    raw_difference=bath_diff,
                    adjustment_rate=cls.BATHROOM_ADJUSTMENT_RATE,
                    adjustment_amount=round(bath_adj, 2),
                    rationale=f"Subject has {abs(bath_diff)} {'more' if bath_diff > 0 else 'fewer'} bathroom(s)",
                )
            )

        # 4. Age / Year Built adjustment
        year_diff = subject.year_built - comp.year_built
        age_adj = year_diff * cls.AGE_ADJUSTMENT_RATE
        if year_diff != 0:
            adjustments.append(
                FeatureAdjustment(
                    feature_name="Year Built / Effective Age",
                    subject_value=subject.year_built,
                    comp_value=comp.year_built,
                    raw_difference=float(year_diff),
                    adjustment_rate=cls.AGE_ADJUSTMENT_RATE,
                    adjustment_amount=round(age_adj, 2),
                    rationale=f"Subject is {abs(year_diff)} year(s) {'newer' if year_diff > 0 else 'older'} than comp",
                )
            )

        # 5. Condition adjustment
        subj_cond_rank = CONDITION_RANKS.get(subject.condition, 3)
        comp_cond_rank = CONDITION_RANKS.get(comp.condition, 3)
        cond_rank_diff = subj_cond_rank - comp_cond_rank
        cond_adj = cond_rank_diff * cls.CONDITION_ADJUSTMENT_RATE
        if cond_rank_diff != 0:
            adjustments.append(
                FeatureAdjustment(
                    feature_name="Property Condition",
                    subject_value=subject.condition.value,
                    comp_value=comp.condition.value,
                    raw_difference=float(cond_rank_diff),
                    adjustment_rate=cls.CONDITION_ADJUSTMENT_RATE,
                    adjustment_amount=round(cond_adj, 2),
                    rationale=f"Subject condition ({subject.condition.value}) vs comp ({comp.condition.value})",
                )
            )

        # 6. Parking spaces adjustment
        parking_diff = subject.parking_spaces - comp.parking_spaces
        parking_adj = parking_diff * cls.PARKING_ADJUSTMENT_RATE
        if parking_diff != 0:
            adjustments.append(
                FeatureAdjustment(
                    feature_name="Parking Spaces",
                    subject_value=subject.parking_spaces,
                    comp_value=comp.parking_spaces,
                    raw_difference=float(parking_diff),
                    adjustment_rate=cls.PARKING_ADJUSTMENT_RATE,
                    adjustment_amount=round(parking_adj, 2),
                    rationale=f"Subject has {abs(parking_diff)} {'more' if parking_diff > 0 else 'fewer'} parking space(s)",
                )
            )

        # 7. Amenities differential
        subj_am = set(a.lower().strip() for a in subject.amenities)
        comp_am = set(a.lower().strip() for a in comp.amenities)
        missing_in_comp = subj_am - comp_am
        extra_in_comp = comp_am - subj_am
        amenity_net_diff = len(missing_in_comp) - len(extra_in_comp)
        amenity_adj = amenity_net_diff * cls.AMENITY_ITEM_VALUE
        if amenity_net_diff != 0:
            adjustments.append(
                FeatureAdjustment(
                    feature_name="Amenities Differential",
                    subject_value=f"{len(subj_am)} amenities",
                    comp_value=f"{len(comp_am)} amenities",
                    raw_difference=float(amenity_net_diff),
                    adjustment_rate=cls.AMENITY_ITEM_VALUE,
                    adjustment_amount=round(amenity_adj, 2),
                    rationale=f"Net amenity adjustment for key features difference ({amenity_net_diff:+d} items)",
                )
            )

        total_net_adjustment = sum(a.adjustment_amount for a in adjustments)
        base_price = comp.sale_price or (comp.monthly_rent * 180.0 if comp.monthly_rent else 0.0)
        adjusted_price = max(10000.0, base_price + total_net_adjustment)

        return adjustments, total_net_adjustment, round(adjusted_price, 2)


class OutlierDetector:
    """Detects statistical outliers in comparable properties using IQR and Z-Score methods."""

    @classmethod
    def detect_outliers(
        cls, comparables: List[ComparableProperty]
    ) -> Tuple[List[ComparableProperty], int]:
        """Tag outliers on adjusted prices using IQR and Z-score tests."""
        if len(comparables) < 4:
            # Insufficient sample size for robust statistical outlier tagging
            return comparables, 0

        prices = np.array([c.adjusted_price for c in comparables], dtype=float)

        # 1. IQR Method
        q25, q75 = np.percentile(prices, 25), np.percentile(prices, 75)
        iqr = q75 - q25
        lower_iqr = q25 - 1.5 * iqr
        upper_iqr = q75 + 1.5 * iqr

        # 2. Z-Score Method
        mean_p = np.mean(prices)
        std_p = np.std(prices)
        z_threshold = 2.0

        outlier_count = 0
        tagged_comps = []

        for comp in comparables:
            p = comp.adjusted_price
            z_score = abs(p - mean_p) / std_p if std_p > 0 else 0.0

            is_iqr_outlier = bool(p < lower_iqr or p > upper_iqr)
            is_z_outlier = bool(z_score > z_threshold)

            is_outlier = is_iqr_outlier or is_z_outlier
            if is_outlier:
                outlier_count += 1

            # Update outlier status on comparable
            updated_comp = comp.model_copy(update={"is_outlier": is_outlier})
            tagged_comps.append(updated_comp)

        return tagged_comps, outlier_count


class CMAEngine:
    """Core Comparative Market Analysis engine."""

    def __init__(
        self,
        similarity_calculator: Optional[SimilarityCalculator] = None,
        min_similarity_threshold: float = 0.50,
        max_comps_to_select: int = 6,
    ):
        self.similarity_calc = similarity_calculator or SimilarityCalculator()
        self.min_similarity_threshold = min_similarity_threshold
        self.max_comps_to_select = max_comps_to_select

    def generate_cma(
        self, subject: PropertyProfile, market_records: List[MarketRecord]
    ) -> Tuple[List[ComparableProperty], CMAAnalysis]:
        """Perform full CMA analysis on market records against subject property."""
        scored_comps: List[ComparableProperty] = []

        for record in market_records:
            sim_score = self.similarity_calc.calculate_similarity(subject, record)
            if sim_score < self.min_similarity_threshold:
                continue

            adjustments, net_adj, adj_price = AdjustmentEngine.calculate_adjustments(subject, record)
            adj_psf = round(adj_price / subject.sqft, 2)

            # Plain-language selection rationale
            rationale = (
                f"Selected with {sim_score * 100:.1f}% similarity. "
                f"Located {record.distance_miles:.2f} miles away. "
                f"{record.bedrooms}B/{record.bathrooms}Ba, {record.sqft:,.0f} sqft, built {record.year_built}. "
                f"Net adjustment: {net_adj:+,.0f} (adjusted price: ${adj_price:,.0f})."
            )

            comp_prop = ComparableProperty(
                record=record,
                similarity_score=sim_score,
                adjustments=adjustments,
                total_net_adjustment=net_adj,
                adjusted_price=adj_price,
                adjusted_price_psf=adj_psf,
                selection_rationale=rationale,
                is_outlier=False,
            )
            scored_comps.append(comp_prop)

        # Sort by similarity descending
        scored_comps.sort(key=lambda c: c.similarity_score, reverse=True)
        selected_comps = scored_comps[: self.max_comps_to_select]

        if not selected_comps:
            # Handle sparse / zero comps gracefully
            empty_cma = CMAAnalysis(
                subject_property_id=subject.property_id,
                comparables=[],
                unadjusted_median_price=0.0,
                unadjusted_mean_price=0.0,
                adjusted_median_price=0.0,
                adjusted_mean_price=0.0,
                adjusted_price_low=0.0,
                adjusted_price_high=0.0,
                adjusted_psf_mean=0.0,
                outlier_count=0,
                methodology_notes="No comparable properties met the minimum similarity criteria.",
            )
            return [], empty_cma

        # Run statistical outlier detection
        tagged_comps, outlier_count = OutlierDetector.detect_outliers(selected_comps)

        # Non-outlier comps used for primary synthesis
        valid_comps = [c for c in tagged_comps if not c.is_outlier]
        eval_comps = valid_comps if valid_comps else tagged_comps

        unadj_prices = [
            c.record.sale_price or (c.record.monthly_rent * 180.0 if c.record.monthly_rent else 0.0)
            for c in eval_comps
        ]
        adj_prices = [c.adjusted_price for c in eval_comps]
        adj_psfs = [c.adjusted_price_psf for c in eval_comps]

        cma_analysis = CMAAnalysis(
            subject_property_id=subject.property_id,
            comparables=tagged_comps,
            unadjusted_median_price=round(float(np.median(unadj_prices)), 2),
            unadjusted_mean_price=round(float(np.mean(unadj_prices)), 2),
            adjusted_median_price=round(float(np.median(adj_prices)), 2),
            adjusted_mean_price=round(float(np.mean(adj_prices)), 2),
            adjusted_price_low=round(float(np.min(adj_prices)), 2),
            adjusted_price_high=round(float(np.max(adj_prices)), 2),
            adjusted_psf_mean=round(float(np.mean(adj_psfs)), 2),
            outlier_count=outlier_count,
            methodology_notes=(
                f"CMA evaluated {len(tagged_comps)} comparable properties. "
                f"Multi-attribute similarity weights applied. "
                f"Appraisal adjustments applied for GLA, bed/bath count, age, condition, parking, and amenities. "
                f"{outlier_count} statistical outlier(s) detected via IQR/Z-score."
            ),
        )

        return tagged_comps, cma_analysis
