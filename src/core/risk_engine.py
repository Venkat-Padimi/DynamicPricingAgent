"""Risk Assessment and Data Quality Engine."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np

from src.core.enums import ConfidenceLevel, PropertyCondition, RiskSeverity
from src.core.models import (
    CMAAnalysis,
    ComparableProperty,
    MarketConditions,
    PropertyProfile,
    RentalPricingResult,
    RentRollSummary,
    RiskItem,
    RiskReport,
    ValuationResult,
)


class RiskQualityEngine:
    """Comprehensive data quality auditor and valuation/pricing risk analyzer."""

    @classmethod
    def evaluate_risks(
        cls,
        subject: PropertyProfile,
        comparables: List[ComparableProperty],
        cma_analysis: Optional[CMAAnalysis] = None,
        market_conditions: Optional[MarketConditions] = None,
        rent_roll_summary: Optional[RentRollSummary] = None,
        valuation: Optional[ValuationResult] = None,
        rental_pricing: Optional[RentalPricingResult] = None,
    ) -> RiskReport:
        """Run all data quality and operational risk checks to produce a structured RiskReport."""
        items: List[RiskItem] = []

        is_stale = False
        is_insufficient = False
        is_missing_roll = False
        is_conflicting = False
        high_variance = False

        valid_comps = [c for c in comparables if not c.is_outlier]
        n_comps = len(valid_comps)

        # 1. Comparable Count & Insufficiency Check
        if n_comps == 0:
            is_insufficient = True
            items.append(
                RiskItem(
                    risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                    severity=RiskSeverity.CRITICAL,
                    category="COMP_DATA",
                    message="Zero valid comparable sales identified within target geographic and similarity parameters.",
                    affected_fields=["comparables", "cma_sales_component"],
                    recommendation="Expand geographic radius or broaden acceptable square footage parameters to acquire comps.",
                )
            )
        elif n_comps < 3:
            is_insufficient = True
            items.append(
                RiskItem(
                    risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                    severity=RiskSeverity.HIGH,
                    category="COMP_DATA",
                    message=f"Insufficient comparable sales ({n_comps} found; minimum of 3 required for institutional standard).",
                    affected_fields=["comparables", "cma_sales_component"],
                    recommendation="Request additional evidence or inspect secondary adjacent micro-markets.",
                )
            )
        elif n_comps == 3:
            items.append(
                RiskItem(
                    risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                    severity=RiskSeverity.MEDIUM,
                    category="COMP_DATA",
                    message="Marginal comparable property count (3 found). Valuation is sensitive to individual transaction variance.",
                    affected_fields=["comparables"],
                    recommendation="Cross-check against pending sales or active listings where available.",
                )
            )

        # 2. Data Freshness Check (Transactions > 12 months)
        now_year = datetime.now(timezone.utc).year
        for comp in comparables:
            tx_date = comp.record.transaction_date
            try:
                tx_dt = datetime.strptime(tx_date, "%Y-%m-%d")
                days_old = (datetime.now(timezone.utc) - tx_dt.replace(tzinfo=timezone.utc)).days
                if days_old > 365:
                    is_stale = True
                    items.append(
                        RiskItem(
                            risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                            severity=RiskSeverity.MEDIUM,
                            category="FRESHNESS",
                            message=f"Comparable '{comp.record.record_id}' transaction date ({tx_date}) exceeds 12 months.",
                            affected_fields=["transaction_date", "comparables"],
                            recommendation="Apply market appreciation time-adjustments or replace with recent transactions.",
                        )
                    )
                    break
            except ValueError:
                pass

        # 3. Outlier Detection Alert
        if cma_analysis and cma_analysis.outlier_count > 0:
            items.append(
                RiskItem(
                    risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                    severity=RiskSeverity.MEDIUM,
                    category="OUTLIER",
                    message=f"{cma_analysis.outlier_count} statistical outlier(s) detected and segregated from primary CMA baseline.",
                    affected_fields=["outlier_count", "adjusted_mean_price"],
                    recommendation="Examine outlier record details to verify whether atypical terms or distress influenced transaction price.",
                )
            )

        # 4. Price Variance / Dispersion Check
        if n_comps >= 2:
            adj_prices = [c.adjusted_price for c in valid_comps]
            mean_p = float(np.mean(adj_prices))
            std_p = float(np.std(adj_prices))
            cv = (std_p / mean_p) if mean_p > 0 else 0.0

            if cv > 0.15:
                high_variance = True
                items.append(
                    RiskItem(
                        risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                        severity=RiskSeverity.HIGH,
                        category="VARIANCE",
                        message=f"High price dispersion among comparables (Coefficient of Variation = {cv:.1%}).",
                        affected_fields=["adjusted_price", "valuation_range"],
                        recommendation="Review feature adjustments or verify whether micro-location school boundary or view premium exists.",
                    )
                )

        # 5. Rent Roll & Lease Operational Risk
        if rent_roll_summary is None or rent_roll_summary.total_units == 0:
            if subject.property_type.value in ["MultiFamily", "Commercial"]:
                is_missing_roll = True
                items.append(
                    RiskItem(
                        risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                        severity=RiskSeverity.HIGH,
                        category="RENT_ROLL",
                        message="Income-producing property lacks operational rent roll and lease schedule.",
                        affected_fields=["rent_roll", "income_capitalization_component"],
                        recommendation="Obtain certified rent roll to enable income-approach valuation capitalization.",
                    )
                )
        else:
            if rent_roll_summary.cliff_risk_level == "HIGH":
                items.append(
                    RiskItem(
                        risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                        severity=RiskSeverity.HIGH,
                        category="RENT_ROLL",
                        message=(
                            f"Critical lease expiration cliff: {rent_roll_summary.lease_turnover_exposure_pct:.1f}% "
                            f"of units roll over within 90 days (${rent_roll_summary.expiring_rent_within_90_days:,.0f}/mo at risk)."
                        ),
                        affected_fields=["lease_turnover_exposure_pct", "expiring_within_90_days"],
                        recommendation="Initiate proactive tenant retention program and budget for turnover concessions.",
                    )
                )

        # 6. Conflicting Data Check
        if rental_pricing and rental_pricing.rent_gap_percentage is not None:
            if abs(rental_pricing.rent_gap_percentage) > 35.0:
                is_conflicting = True
                items.append(
                    RiskItem(
                        risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                        severity=RiskSeverity.MEDIUM,
                        category="CONFLICTING_DATA",
                        message=(
                            f"In-place rent diverges by {rental_pricing.rent_gap_percentage:+.1f}% from market recommendation "
                            f"(${rental_pricing.rent_gap_amount:+,.0f}/mo gap)."
                        ),
                        affected_fields=["rent_gap_amount", "rent_gap_percentage"],
                        recommendation="Confirm whether below-market rent is locked by long-term lease or subsidized covenants.",
                    )
                )

        # 7. Unusual Property Characteristics
        if subject.age_years > 75 and subject.condition in [PropertyCondition.FAIR, PropertyCondition.POOR]:
            items.append(
                RiskItem(
                    risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                    severity=RiskSeverity.MEDIUM,
                    category="PROPERTY_CHARACTERISTICS",
                    message=f"Property built in {subject.year_built} ({subject.age_years} yrs) with '{subject.condition.value}' condition rating.",
                    affected_fields=["year_built", "condition"],
                    recommendation="Commission structural and MEP physical engineering inspection before capital commitment.",
                )
            )

        # 8. Low Confidence Warning
        if valuation and valuation.confidence_level == ConfidenceLevel.LOW:
            items.append(
                RiskItem(
                    risk_id=f"RISK-{uuid.uuid4().hex[:6].upper()}",
                    severity=RiskSeverity.HIGH,
                    category="CONFIDENCE",
                    message=f"Valuation confidence score is LOW ({valuation.confidence_score:.1f}/100).",
                    affected_fields=["confidence_score", "confidence_level"],
                    recommendation="Mandatory on-site appraisal inspection required before executing pricing decisions.",
                )
            )

        # Calculate Data Quality Score (0 to 100)
        penalty = 0.0
        for it in items:
            if it.severity == RiskSeverity.CRITICAL:
                penalty += 35.0
            elif it.severity == RiskSeverity.HIGH:
                penalty += 18.0
            elif it.severity == RiskSeverity.MEDIUM:
                penalty += 8.0
            else:
                penalty += 3.0

        quality_score = float(np.clip(100.0 - penalty, 10.0, 100.0))

        # Overall severity assignment
        critical_count = sum(1 for it in items if it.severity == RiskSeverity.CRITICAL)
        high_count = sum(1 for it in items if it.severity == RiskSeverity.HIGH)
        med_count = sum(1 for it in items if it.severity == RiskSeverity.MEDIUM)

        if critical_count > 0:
            overall_sev = RiskSeverity.CRITICAL
        elif high_count >= 1 or quality_score < 60.0:
            overall_sev = RiskSeverity.HIGH
        elif med_count >= 1 or quality_score < 80.0:
            overall_sev = RiskSeverity.MEDIUM
        else:
            overall_sev = RiskSeverity.LOW

        summary_text = (
            f"Risk assessment identified {len(items)} item(s) (Overall Severity: {overall_sev.value}, "
            f"Data Quality Score: {quality_score:.1f}/100). "
            f"{'Stale market data flagged. ' if is_stale else ''}"
            f"{'Insufficient comparables flagged. ' if is_insufficient else ''}"
            f"{'High price variance detected. ' if high_variance else ''}"
            f"{'Conflicting rent data flagged. ' if is_conflicting else ''}"
        ).strip()

        return RiskReport(
            overall_risk_severity=overall_sev,
            data_quality_score=round(quality_score, 1),
            is_stale_data=is_stale,
            is_insufficient_comps=is_insufficient,
            is_missing_rentroll=is_missing_roll,
            is_conflicting_data=is_conflicting,
            high_variance_warning=high_variance,
            items=items,
            summary=summary_text,
        )
