"""Deterministic Confidence Scoring Engine."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.core.enums import ConfidenceLevel
from src.core.models import ComparableProperty, MarketConditions, RentRollSummary


class ConfidenceScoringEngine:
    """Calculates deterministic confidence scores based on objective data quality metrics."""

    @classmethod
    def calculate_confidence(
        cls,
        comparables: List[ComparableProperty],
        market_conditions: Optional[MarketConditions] = None,
        rent_roll_summary: Optional[RentRollSummary] = None,
        has_complete_specs: bool = True,
    ) -> Tuple[ConfidenceLevel, float, Dict[str, Any]]:
        """Compute score from 0.0 to 100.0 and map to HIGH, MEDIUM, LOW tier."""
        valid_comps = [c for c in comparables if not c.is_outlier]
        eval_comps = valid_comps if valid_comps else comparables
        n_comps = len(eval_comps)

        breakdown: Dict[str, Any] = {}

        # 1. Number of comparable properties (max 25 pts)
        if n_comps >= 5:
            count_pts = 25.0
        elif n_comps == 4:
            count_pts = 20.0
        elif n_comps == 3:
            count_pts = 15.0
        elif n_comps == 2:
            count_pts = 10.0
        elif n_comps == 1:
            count_pts = 5.0
        else:
            count_pts = 0.0
        breakdown["comps_count_pts"] = count_pts

        # 2. Average similarity score (max 20 pts)
        if n_comps > 0:
            avg_sim = float(np.mean([c.similarity_score for c in eval_comps]))
            if avg_sim >= 0.88:
                sim_pts = 20.0
            elif avg_sim >= 0.75:
                sim_pts = 15.0
            elif avg_sim >= 0.60:
                sim_pts = 10.0
            else:
                sim_pts = 5.0
        else:
            avg_sim = 0.0
            sim_pts = 0.0
        breakdown["similarity_avg"] = round(avg_sim, 3)
        breakdown["similarity_pts"] = sim_pts

        # 3. Geographic proximity (max 15 pts)
        if n_comps > 0:
            avg_dist = float(np.mean([c.record.distance_miles for c in eval_comps]))
            if avg_dist <= 0.35:
                dist_pts = 15.0
            elif avg_dist <= 0.75:
                dist_pts = 12.0
            elif avg_dist <= 1.5:
                dist_pts = 8.0
            elif avg_dist <= 3.0:
                dist_pts = 4.0
            else:
                dist_pts = 1.0
        else:
            avg_dist = 99.0
            dist_pts = 0.0
        breakdown["mean_distance_miles"] = round(avg_dist, 2)
        breakdown["proximity_pts"] = dist_pts

        # 4. Adjusted price variance / dispersion (max 15 pts)
        if n_comps >= 2:
            prices = [c.adjusted_price for c in eval_comps]
            mean_p = float(np.mean(prices))
            std_p = float(np.std(prices))
            cv = (std_p / mean_p) if mean_p > 0 else 1.0

            if cv <= 0.04:
                var_pts = 15.0
            elif cv <= 0.08:
                var_pts = 12.0
            elif cv <= 0.12:
                var_pts = 8.0
            elif cv <= 0.18:
                var_pts = 4.0
            else:
                var_pts = 1.0
        elif n_comps == 1:
            cv = 0.0
            var_pts = 6.0
        else:
            cv = 1.0
            var_pts = 0.0
        breakdown["coefficient_of_variation"] = round(cv, 4)
        breakdown["variance_pts"] = var_pts

        # 5. Data completeness and macro trend coverage (max 25 pts)
        completeness_pts = 0.0
        if market_conditions is not None and len(market_conditions.historical_points) >= 6:
            completeness_pts += 10.0
        elif market_conditions is not None:
            completeness_pts += 5.0

        if rent_roll_summary is not None and rent_roll_summary.total_units > 0:
            completeness_pts += 10.0

        if has_complete_specs:
            completeness_pts += 5.0

        breakdown["completeness_pts"] = completeness_pts

        total_score = round(
            float(np.clip(count_pts + sim_pts + dist_pts + var_pts + completeness_pts, 0.0, 100.0)),
            1,
        )
        breakdown["total_score"] = total_score

        if total_score >= 75.0:
            level = ConfidenceLevel.HIGH
        elif total_score >= 50.0:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        breakdown["confidence_level"] = level.value
        return level, total_score, breakdown
