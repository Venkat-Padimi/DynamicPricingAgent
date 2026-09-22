"""Compliance Dossier Reporter: Generates institutional Markdown and structured JSON export dossiers."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.enums import DataOrigin, ReviewStatus, RiskSeverity
from src.core.formatters import (
    CURRENCY_CODE,
    CURRENCY_SYMBOL,
    format_bhk,
    format_inr,
    format_inr_short,
    format_psf,
    format_rent,
)
from src.core.models import (
    LEGAL_DISCLAIMER_TEXT,
    SYNTHETIC_NOTICE_TEXT,
    AuditEntry,
    CMAAnalysis,
    ComparableProperty,
    HumanReviewDecision,
    MarketConditions,
    MarketRecord,
    PropertyProfile,
    RentalPricingResult,
    RentRollSummary,
    RentRollUnit,
    RiskReport,
    ValuationResult,
)
from src.core.state import AgentWorkflowState


class ComplianceDossierReporter:
    """Institutional reporting engine producing auditable Markdown compliance dossiers and JSON exports in INR."""

    def __init__(self, platform_version: str = "1.0.0"):
        self.platform_version = platform_version

    def generate_markdown_dossier(self, state: AgentWorkflowState) -> str:
        """Generate a complete, publication-ready Executive Markdown Compliance Dossier (.md)."""
        lines: List[str] = []
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        profile: Optional[PropertyProfile] = state.get("property_profile")
        val: Optional[ValuationResult] = state.get("valuation")
        pricing: Optional[RentalPricingResult] = state.get("rental_pricing")
        cma: Optional[CMAAnalysis] = state.get("cma_analysis")
        comps: List[ComparableProperty] = state.get("comparables", [])
        market: Optional[MarketConditions] = state.get("market_conditions")
        rent_summary: Optional[RentRollSummary] = state.get("rent_roll_summary")
        rent_units: List[RentRollUnit] = state.get("rent_roll_units", [])
        risk: Optional[RiskReport] = state.get("risk_report")
        review: Optional[HumanReviewDecision] = state.get("human_review")
        audit_trail: List[AuditEntry] = state.get("audit_trail", [])
        workflow_status = state.get("workflow_status", "UNKNOWN")

        prop_id = profile.property_id if profile else "UNSPECIFIED"
        prop_addr = profile.address if profile else "Unknown Address"
        prop_loc = f"{profile.city}, {profile.state} (PIN: {profile.zip_code})" if profile else ""

        # ---------------------------------------------------------------------
        # 1. Document Header & Report Metadata
        # ---------------------------------------------------------------------
        lines.append("# Institutional Valuation & Dynamic Pricing Compliance Dossier (India)")
        lines.append(f"**Asset Identification:** `{prop_id}` — {prop_addr}, {prop_loc}")
        lines.append(f"**Dossier Generation Timestamp:** `{now_utc}` | **Platform Engine Version:** `v{self.platform_version}`")
        lines.append(f"**Workflow Execution Status:** `{workflow_status}`")
        lines.append("")

        # ---------------------------------------------------------------------
        # 2. Mandatory Disclaimers & Provenance Notice (Critical Alert)
        # ---------------------------------------------------------------------
        lines.append("> [!IMPORTANT]")
        lines.append("> **MANDATORY LEGAL & DECISION-SUPPORT DISCLAIMER:**")
        lines.append(f"> {LEGAL_DISCLAIMER_TEXT}")
        lines.append("> ")
        lines.append("> **DECISION-SUPPORT NOTICE:** This system is an automated AI decision-support platform, ")
        lines.append("> NOT a registered valuation under the Companies Act or an appraisal under Indian law. All calculated figures ")
        lines.append("> represent analytical recommendations and require explicit Human-in-the-Loop review and professional validation.")
        lines.append("")
        lines.append("> [!WARNING]")
        lines.append("> **DATA PROVENANCE & SYNTHETIC DEMONSTRATION DISCLOSURE:**")
        lines.append(f"> {SYNTHETIC_NOTICE_TEXT}")
        lines.append("> All comparable sales, rental listings, rent-roll schedules, and submarket trend data used in ")
        lines.append("> this dossier are mathematically calibrated synthetic fixtures for institutional system demonstration.")
        lines.append("")

        # ---------------------------------------------------------------------
        # 3. Executive Valuation & Dynamic Pricing Recommendation Summary
        # ---------------------------------------------------------------------
        lines.append("## 1. Executive Summary & Recommendation Overview")
        lines.append("")
        lines.append("*The following section summarizes the primary valuation and pricing recommendations in Indian Rupees (INR). ")
        lines.append("Quantitative figures represent deterministic mathematical calculations; strategic commentary ")
        lines.append("represents decision-support recommendations subject to human review.*")
        lines.append("")

        # Valuation Recommendation Block
        if val:
            conf_color = "🟢 HIGH" if val.confidence_score >= 80 else ("🟡 MEDIUM" if val.confidence_score >= 60 else "🔴 LOW")
            lines.append("### Valuation Determination")
            lines.append("| Metric | Calculated Value | Analytical Description |")
            lines.append("| :--- | :--- | :--- |")
            lines.append(f"| **Estimated Market Value** | **{format_inr(val.estimated_value, use_words=True)}** | Primary deterministic multi-component estimate |")
            lines.append(f"| **Valuation Range** | **{format_inr(val.valuation_range_low)} — {format_inr(val.valuation_range_high)}** | Empirical lower & upper boundaries |")
            lines.append(f"| **Price per Sq Ft** | **{format_psf(val.valuation_psf)}** | Based on built-up living area |")
            lines.append(f"| **Confidence Level** | **{conf_color}** (`{val.confidence_score:.1f}/100`) | Multi-factor data reliability score |")
            lines.append("")

            bd = val.breakdown
            income_val_str = format_inr(bd.income_capitalization_component, use_words=True) if bd.income_capitalization_component is not None else "N/A"
            lines.append("#### Deterministic Component Weight Allocation")
            lines.append("| Component Model | Applied Weight | Contribution Value | Contribution Description |")
            lines.append("| :--- | :--- | :--- | :--- |")
            lines.append(f"| **CMA Adjusted Sales** | {bd.cma_weight*100:.1f}% | {format_inr(bd.cma_sales_component, use_words=True)} | Appraisal-adjusted comparable transactions |")
            lines.append(f"| **Submarket Trend PSF** | {bd.market_trend_weight*100:.1f}% | {format_inr(bd.market_trend_component, use_words=True)} | 24-month historical trend price index |")
            lines.append(f"| **Location & Quality** | {bd.location_weight*100:.1f}% | {format_inr(bd.location_component, use_words=True)} | Condition, age, and amenity factor |")
            lines.append(f"| **Income Capitalization** | {bd.income_weight*100:.1f}% | {income_val_str} | Capitalized gross/net yield |")
            lines.append("")
        else:
            lines.append("*Valuation calculation is not yet executed or unavailable.*")
            lines.append("")

        # Dynamic Rental Pricing Block
        if pricing:
            lines.append("### Dynamic Rental Pricing Recommendation")
            lines.append("| Pricing Tier | Monthly Rent | Strategic Purpose |")
            lines.append("| :--- | :--- | :--- |")
            lines.append(f"| **Floor Rate** | **{format_rent(pricing.recommended_rent_range_low)}** | Defensive rate for accelerated lease-up velocity |")
            lines.append(f"| **Recommended Midpoint** | **{format_rent(pricing.recommended_midpoint)}** | Optimal risk-adjusted target market rent |")
            lines.append(f"| **Ceiling Rate** | **{format_rent(pricing.recommended_rent_range_high)}** | Maximum yield target during peak demand |")
            lines.append("")

            if pricing.current_in_place_rent is not None:
                gap_amt = pricing.rent_gap_amount if pricing.rent_gap_amount is not None else (pricing.recommended_midpoint - pricing.current_in_place_rent)
                gap_pct = pricing.rent_gap_percentage if pricing.rent_gap_percentage is not None else (gap_amt / max(pricing.current_in_place_rent, 1.0) * 100.0)
                gap_sign = "+" if gap_amt >= 0 else ""
                lines.append(f"- **Current In-Place Rent:** `{format_rent(pricing.current_in_place_rent)}`")
                lines.append(f"- **In-Place Rent Gap:** `{gap_sign}{format_inr(gap_amt)} / mo` (`{gap_sign}{gap_pct:.1f}%`) relative to target market rent.")
            if pricing.pricing_drivers:
                lines.append(f"- **Primary Pricing Drivers:** {'; '.join(pricing.pricing_drivers)}")
            lines.append(f"- **Seasonal / Momentum Adjustments:** {pricing.seasonal_factors}")
            lines.append("")
        else:
            lines.append("*Dynamic rental pricing calculation is not yet executed or unavailable.*")
            lines.append("")

        # ---------------------------------------------------------------------
        # 4. Property Overview & Valuation Context
        # ---------------------------------------------------------------------
        lines.append("## 2. Subject Property Overview & Specifications")
        lines.append("")
        if profile:
            lines.append("| Property Attribute | Specification | Property Attribute | Specification |")
            lines.append("| :--- | :--- | :--- | :--- |")
            lines.append(f"| **Property ID** | `{profile.property_id}` | **Property Type** | `{profile.property_type.value}` |")
            lines.append(f"| **Address** | {profile.address} | **City, State (PIN)** | {profile.city}, {profile.state} (PIN: {profile.zip_code}) |")
            carpet_disp = f"{profile.carpet_area_sqft:,.0f} sq ft" if profile.carpet_area_sqft else "Not specified"
            lines.append(f"| **Super Built-up Area** | {profile.sqft:,.0f} sq ft | **RERA Carpet Area** | {carpet_disp} |")
            lines.append(f"| **Layout / Configuration** | {profile.bhk_display} ({profile.bathrooms:.0f} Bath) | **Property Condition** | `{profile.condition.value}` |")
            lines.append(f"| **Year Built** | {profile.year_built} (Age: {profile.age_years} yrs) | **Reserved Parking** | {profile.parking_spaces} covered space(s) |")
            occ_str = f"{profile.occupancy_rate * 100:.1f}%" if profile.occupancy_rate is not None else "N/A"
            lines.append(f"| **Monthly Maintenance** | {format_rent(profile.hoa_monthly)} | **Current Occupancy** | {occ_str} |")
            amenities_str = ", ".join(profile.amenities) if profile.amenities else "None reported"
            lines.append(f"| **Key Amenities** | {amenities_str} | **Data Origin** | `{profile.data_origin.value}` |")
            lines.append("")
        else:
            lines.append("*Property profile not provided.*")
            lines.append("")

        # ---------------------------------------------------------------------
        # 5. Data Provenance & Integrity Matrix
        # ---------------------------------------------------------------------
        lines.append("## 3. Data Provenance & Source Integrity Matrix")
        lines.append("")
        lines.append("Every record ingested by the multi-agent system carries explicit provenance metadata to prevent ")
        lines.append("unverified claims and ensure auditable traceability.")
        lines.append("")
        lines.append("| Data Layer | Consulted Source | Origin Classification | Records Inspected | Provenance / Compliance Notice |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")

        subj_source = profile.provenance.source if profile and profile.provenance else "Intake User Interface"
        subj_origin = profile.data_origin.value if profile else "USER-PROVIDED"
        lines.append(f"| **Subject Asset** | {subj_source} | `{subj_origin}` | 1 record | User-provided property specifications |")

        sales_records: List[MarketRecord] = state.get("sales_records", [])
        sales_source = sales_records[0].provenance.source if sales_records and sales_records[0].provenance else "Synthetic Demonstration Provider v1.0"
        lines.append(f"| **Sales Transactions** | {sales_source} | `SYNTHETIC DEMONSTRATION DATA` | {len(sales_records)} comps queried | {SYNTHETIC_NOTICE_TEXT} |")

        rental_records: List[MarketRecord] = state.get("rental_records", [])
        rental_source = rental_records[0].provenance.source if rental_records and rental_records[0].provenance else "Synthetic Demonstration Provider v1.0"
        lines.append(f"| **Rental Transactions** | {rental_source} | `SYNTHETIC DEMONSTRATION DATA` | {len(rental_records)} listings queried | {SYNTHETIC_NOTICE_TEXT} |")

        trend_pts = market.historical_points if market else []
        lines.append(f"| **Submarket Trends** | Submarket Trend Provider v1.0 | `SYNTHETIC DEMONSTRATION DATA` | {len(trend_pts)} historical periods | {SYNTHETIC_NOTICE_TEXT} |")

        lines.append(f"| **Operational Rent Roll** | Rent Roll Provider v1.0 | `SYNTHETIC DEMONSTRATION DATA` | {len(rent_units)} units audited | Anonymized tenant records (Zero PII exposure) |")
        lines.append("")

        # ---------------------------------------------------------------------
        # 6. Comparative Market Analysis (CMA) & Feature Adjustments
        # ---------------------------------------------------------------------
        lines.append("## 4. Comparative Market Analysis (CMA) & Feature Adjustments")
        lines.append("")
        if cma and comps:
            lines.append(f"**CMA Selection Summary:** Evaluated against candidate comps within a search radius of "
                         f"`{state.get('search_radius_miles', 1.5):.1f} miles ({state.get('search_radius_miles', 1.5)*1.60934:.1f} km)`. "
                         f"Top {len(comps)} comps selected by multi-attribute similarity.")
            lines.append("")
            lines.append(f"- **Median Comparable Adjusted Value:** `{format_inr(cma.adjusted_median_price, use_words=True)}`")
            lines.append(f"- **Mean Comparable Adjusted Value:** `{format_inr(cma.adjusted_mean_price, use_words=True)}`")
            lines.append(f"- **CMA Price Spread:** `{format_inr_short(cma.adjusted_price_low)} — {format_inr_short(cma.adjusted_price_high)}` (Outliers Identified: {cma.outlier_count})")
            lines.append("")

            lines.append("### Selected Comparable Properties")
            lines.append("| Address | Distance | Sim Score | Sale Date | Sale Price | Net Adjustments | Adjusted Price | Outlier Status |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for c in comps:
                outlier_badge = "⚠️ Outlier" if c.is_outlier else "✅ Normal"
                net_sign = "+" if c.total_net_adjustment >= 0 else ""
                sale_price_str = format_inr(c.record.sale_price) if c.record.sale_price else "N/A"
                sale_date_str = c.record.transaction_date or "Recent"
                lines.append(
                    f"| {c.record.address} | {c.record.distance_km:.2f} km | `{c.similarity_score:.3f}` | "
                    f"{sale_date_str} | {sale_price_str} | {net_sign}₹{c.total_net_adjustment:,.0f} | "
                    f"**{format_inr(c.adjusted_price)}** | {outlier_badge} |"
                )
            lines.append("")

            lines.append("### Step-by-Step Appraisal Feature Adjustments Breakdown")
            lines.append("> **Appraisal Directionality Rule:** Standard appraisal methodology is strictly enforced: ")
            lines.append("> *the comparable property is adjusted to match the subject property* (\\(AdjustedPrice = CompSalePrice + \\sum Adjustments\\)).")
            lines.append("")

            lines.append("| Comparable Address | Size Adj | Beds Adj | Baths Adj | Age Adj | Condition Adj | Amenities Adj | Parking Adj | Total Net (₹) |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for c in comps:
                adj_map = {adj.feature_name.lower(): adj.adjustment_amount for adj in c.adjustments}
                def _fmt(val: float) -> str:
                    if abs(val) < 1.0:
                        return "₹0"
                    return f"{'+' if val > 0 else ''}₹{val:,.0f}"

                size_adj = _fmt(adj_map.get("square footage", 0.0))
                bed_adj = _fmt(adj_map.get("bedrooms", 0.0))
                bath_adj = _fmt(adj_map.get("bathrooms", 0.0))
                age_adj = _fmt(adj_map.get("year built / effective age", 0.0))
                cond_adj = _fmt(adj_map.get("property condition", 0.0))
                amen_adj = _fmt(adj_map.get("amenities differential", 0.0))
                park_adj = _fmt(adj_map.get("parking spaces", 0.0))
                total_net = _fmt(c.total_net_adjustment)

                lines.append(
                    f"| {c.record.address} | {size_adj} | {bed_adj} | {bath_adj} | {age_adj} | {cond_adj} | {amen_adj} | {park_adj} | **{total_net}** |"
                )
            lines.append("")
        else:
            lines.append("*Comparative Market Analysis data is unavailable or not yet generated.*")
            lines.append("")

        # ---------------------------------------------------------------------
        # 7. Submarket Conditions & Historical Trends
        # ---------------------------------------------------------------------
        lines.append("## 5. Submarket Conditions & Historical Trends")
        lines.append("")
        if market:
            lines.append(f"**Submarket Name:** `{market.submarket_name}` | **Historical Window:** {market.time_horizon_months} Months")
            lines.append("")
            lines.append("| Market Signal | Historical Statistic | Classification | Analytical Interpretation |")
            lines.append("| :--- | :--- | :--- | :--- |")
            lines.append(f"| **Annual Sales Price CAGR** | **{market.annual_price_growth_rate:+.1f}% / yr** | Fact (Historical) | 24-month compound annual growth rate |")
            lines.append(f"| **Annual Rental Rate CAGR** | **{market.annual_rent_growth_rate:+.1f}% / yr** | Fact (Historical) | 24-month rental rate index progression |")
            mom_str = f"{market.price_momentum_pct_6m:+.1f}%" if market.price_momentum_pct_6m is not None else "N/A"
            lines.append(f"| **6-Month Price Momentum** | **{mom_str}** | Fact (Historical) | Short-term velocity indicator |")
            lines.append(f"| **Gross Capitalization Yield** | **{market.current_gross_yield_pct:.2f}%** | Fact (Calculated) | Submarket median rent-to-price ratio |")
            dom_str = f"{market.avg_days_on_market:.0f} days" if market.avg_days_on_market is not None else "N/A"
            lines.append(f"| **Median Days on Market (DOM)** | **{dom_str}** | Fact (Historical) | Liquidity and transaction velocity metric |")
            inv_str = f"{market.avg_inventory_months:.1f} months" if market.avg_inventory_months is not None else "N/A"
            lines.append(f"| **Inventory Level** | **{inv_str}** | Fact (Historical) | Current market absorption inventory |")
            lines.append(f"| **Submarket Trend Direction** | **`{market.trend_direction.value}`** | Qualitative Assessment | Strategic macro trajectory classification |")
            lines.append("")
            lines.append(f"**Historical Fact Summary:** {market.factual_summary}")
            lines.append("")
            lines.append(f"**Agent Interpretation:** {market.agent_interpretation}")
            lines.append("")
        else:
            lines.append("*Submarket conditions data unavailable.*")
            lines.append("")

        # ---------------------------------------------------------------------
        # 8. Operational Rent Roll & Expiration Cliff Ladder Analysis
        # ---------------------------------------------------------------------
        lines.append("## 6. Operational Rent Roll & Lease Expiration Analysis")
        lines.append("")
        if rent_summary:
            lines.append("| Lease & Operational Metric | Value | Analytical Significance |")
            lines.append("| :--- | :--- | :--- |")
            lines.append(f"| **Physical Occupancy** | **{rent_summary.physical_occupancy_rate*100:.1f}%** ({rent_summary.occupied_units}/{rent_summary.total_units} units) | In-place occupied percentage |")
            lines.append(f"| **Physical Vacancy** | **{rent_summary.physical_vacancy_rate*100:.1f}%** | Immediate leasing exposure |")
            lines.append(f"| **Gross Potential Monthly Rent** | **{format_rent(rent_summary.gross_potential_monthly_rent)}** | 100% capacity rental yield |")
            lines.append(f"| **In-Place Monthly Rent** | **{format_rent(rent_summary.current_in_place_monthly_rent)}** | Current operating cash flow |")
            lines.append(f"| **Average Rent per Unit** | **{format_rent(rent_summary.avg_rent_per_unit)}** | Weighted average unit revenue |")
            lines.append(f"| **Average Rent per Sq Ft** | **{format_psf(rent_summary.avg_rent_psf)}** | Normalized unit rate |")
            lines.append(f"| **Cumulative Lease Turnover Risk** | **{rent_summary.lease_turnover_exposure_pct:.1f}%** | 90-day combined rollover exposure |")
            lines.append("")

            lines.append("### 30 / 60 / 90-Day Lease Expiration Cliff Ladder")
            lines.append("| Expiration Horizon | Expiring Units | Exposure Rate (%) | Operational Guidance |")
            lines.append("| :--- | :--- | :--- | :--- |")
            tot = max(rent_summary.total_units, 1)
            lines.append(f"| **0 — 30 Days** | **{rent_summary.expiring_within_30_days} units** | {(rent_summary.expiring_within_30_days/tot)*100:.1f}% | Urgent renewal or remarketing required |")
            lines.append(f"| **31 — 60 Days** | **{rent_summary.expiring_within_60_days} units** | {(rent_summary.expiring_within_60_days/tot)*100:.1f}% | Active renewal negotiations window |")
            lines.append(f"| **61 — 90 Days** | **{rent_summary.expiring_within_90_days} units** | {(rent_summary.expiring_within_90_days/tot)*100:.1f}% | Early renewal outreach initiation |")
            lines.append(f"| **> 90 Days (Stable)** | **{rent_summary.expiring_beyond_90_days} units** | {(rent_summary.expiring_beyond_90_days/tot)*100:.1f}% | Medium-to-long-term stable tenancy |")
            lines.append("")

            if rent_units:
                lines.append("### Anonymized Tenant Rent Schedule (Strict PII Protection)")
                lines.append("> **PRIVACY SAFEGUARD:** Tenant identities are pseudonymized tokens (`TENANT-xxx`). ")
                lines.append("> No personally identifiable tenant information (PII) is stored or exported.")
                lines.append("")
                lines.append("| Unit ID | Anonymized Tenant Token | Layout | Area | In-Place Rent | In-Place PSF | Lease End | Status |")
                lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
                for u in rent_units:
                    lines.append(f"| `{u.unit_id}` | `{u.tenant_pseudonym}` | {u.bhk_display}/{u.bathrooms:.0f}Bath | {u.sqft:,.0f} sq ft | {format_rent(u.current_rent)} | {format_psf(u.in_place_psf)} | {u.lease_end} | `{u.lease_status.value}` |")
                lines.append("")
        else:
            lines.append("*Rent roll operational summary is unavailable.*")
            lines.append("")

        # ---------------------------------------------------------------------
        # 9. Risk Assessment & Data Quality Scorecard
        # ---------------------------------------------------------------------
        lines.append("## 7. Risk Assessment & Data Quality Scorecard")
        lines.append("")
        if risk:
            severity_badge = f"⚠️ {risk.overall_risk_severity.value}" if risk.overall_risk_severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL] else f"✅ {risk.overall_risk_severity.value}"
            lines.append(f"- **Overall Risk Severity:** **{severity_badge}**")
            lines.append(f"- **Composite Data Quality Score:** **`{risk.data_quality_score:.1f} / 100`**")
            lines.append(f"- **Identified Audit Flags:** {len(risk.items)} findings recorded")
            lines.append("")

            if risk.items:
                lines.append("| Risk Category | Severity | Diagnostic Finding | Mitigating Action / Recommendation |")
                lines.append("| :--- | :--- | :--- | :--- |")
                for it in risk.items:
                    sev_str = f"`{it.severity.value}`"
                    lines.append(f"| {it.category} | {sev_str} | {it.message} | {it.recommendation} |")
                lines.append("")
            else:
                lines.append("*Zero active risk flags detected.*")
                lines.append("")
        else:
            lines.append("*Risk and data quality audit report is unavailable.*")
            lines.append("")

        # ---------------------------------------------------------------------
        # 10. Human-in-the-Loop Review Sign-Off & Governance
        # ---------------------------------------------------------------------
        lines.append("## 8. Human-in-the-Loop Review Sign-Off & Governance")
        lines.append("")
        lines.append("> **COMPLIANCE MANDATE:** Under platform architectural governance, no pricing or valuation recommendation ")
        lines.append("> can be finalized without explicit human review, attestation, and signature.")
        lines.append("")

        if review:
            status_badge = {
                ReviewStatus.APPROVED: "✅ APPROVED FOR PUBLISHING",
                ReviewStatus.MODIFIED: "✏️ MODIFIED WITH REVIEWER OVERRIDES",
                ReviewStatus.REJECTED: "❌ REJECTED — PRICING HALTED",
                ReviewStatus.EVIDENCE_REQUESTED: "🔄 EVIDENCE REQUESTED — QUERY EXPANDED",
                ReviewStatus.PENDING: "⏳ PENDING REVIEW — AWAITING HUMAN ACTION",
            }.get(review.status, review.status.value)

            lines.append(f"### Review Determination: **{status_badge}**")
            lines.append("")
            lines.append("| Governance Record Field | Recorded Specification |")
            lines.append("| :--- | :--- |")
            lines.append(f"| **Review Status** | `{review.status.value}` |")
            lines.append(f"| **Review Identifier** | `{review.review_id}` |")
            lines.append(f"| **Reviewer Name & Role** | {review.reviewer_name} ({review.reviewer_role}) |")
            lines.append(f"| **Review Timestamp** | `{review.decision_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}` |")
            lines.append(f"| **Reviewer Justification Notes** | *\"{review.reviewer_notes}\"* |")
            val_override = format_inr(review.modified_valuation, use_words=True) if review.modified_valuation else "None (Accepted AI Valuation)"
            rent_override = format_rent(review.modified_recommended_rent) if review.modified_recommended_rent else "None (Accepted AI Rent)"
            lines.append(f"| **Valuation Override Applied** | {val_override} |")
            lines.append(f"| **Rental Pricing Override Applied** | {rent_override} |")
            lines.append("")
        else:
            lines.append("### Review Determination: **⏳ PENDING REVIEW — AWAITING HUMAN ACTION**")
            lines.append("")
            lines.append("| Governance Record Field | Recorded Specification |")
            lines.append("| :--- | :--- |")
            lines.append("| **Review Status** | `PENDING` |")
            lines.append("| **Review Identifier** | `[Awaiting Assignment]` |")
            lines.append("| **Reviewer Name & Role** | `[Unassigned Professional]` |")
            lines.append("| **Review Timestamp** | `[Pending Reviewer Action]` |")
            lines.append("| **Reviewer Justification Notes** | `[Pending Reviewer Input]` |")
            lines.append("| **Valuation Override Applied** | `None` |")
            lines.append("| **Rental Pricing Override Applied** | `None` |")
            lines.append("")

        lines.append("### Formal Human Reviewer Attestation")
        lines.append("```text")
        lines.append("I hereby confirm that I have reviewed the AI-assisted automated valuation and dynamic pricing")
        lines.append("recommendation, inspected the selected comparable properties and feature-level adjustments,")
        lines.append("evaluated the submarket trend metrics and lease-roll expiration ladder, checked data quality and")
        lines.append("risk audit flags, and executed the recorded governance decision above in accordance with")
        lines.append("professional decision-support standards.")
        lines.append("```")
        lines.append("")

        # ---------------------------------------------------------------------
        # 11. Multi-Agent Execution Audit Log
        # ---------------------------------------------------------------------
        lines.append("## 9. Multi-Agent Execution Audit Log")
        lines.append("")
        lines.append("The following table records the immutable chronological trace of agent node executions in the LangGraph workflow:")
        lines.append("")
        if audit_trail:
            lines.append("| Step | Timestamp (UTC) | Agent Node | Action Executed | Latency (ms) | Output Summary | Warnings |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for entry in audit_trail:
                ts_str = entry.timestamp.strftime("%H:%M:%S")
                lat_str = f"{entry.execution_time_ms:.1f} ms" if entry.execution_time_ms is not None else "—"
                warn_str = f"⚠️ {len(entry.warnings_issued)}" if entry.warnings_issued else "None"
                clean_output = entry.outputs_summary.replace("|", "/")
                lines.append(
                    f"| `{entry.step_index}` | `{ts_str}` | **{entry.agent_name}** | `{entry.action}` | {lat_str} | {clean_output} | {warn_str} |"
                )
            lines.append("")
        else:
            lines.append("*No audit entries recorded.*")
            lines.append("")

        # ---------------------------------------------------------------------
        # 12. Closing Legal & Decision-Support Attestation
        # ---------------------------------------------------------------------
        lines.append("---")
        lines.append("### Compliance & Operational Notice")
        lines.append(f"- **Legal Notice:** {LEGAL_DISCLAIMER_TEXT}")
        lines.append(f"- **Data Provenance:** {SYNTHETIC_NOTICE_TEXT}")
        lines.append("- **Export Classification:** Institutional Decision-Support Compliance Dossier")
        lines.append(f"- **System Identity:** Automated Valuation & Dynamic Pricing Agent Platform (India) v{self.platform_version}")
        lines.append("")

        return "\n".join(lines)

    def generate_json_dict(self, state: AgentWorkflowState) -> Dict[str, Any]:
        """Generate a complete, serializable Python dictionary of the workflow state and compliance metadata."""
        now_utc = datetime.now(timezone.utc).isoformat()
        report_id = f"DOSSIER-{uuid.uuid4().hex[:12].upper()}"

        profile = state.get("property_profile")
        val = state.get("valuation")
        pricing = state.get("rental_pricing")
        cma = state.get("cma_analysis")
        comps = state.get("comparables", [])
        market = state.get("market_conditions")
        rent_summary = state.get("rent_roll_summary")
        rent_units = state.get("rent_roll_units", [])
        risk = state.get("risk_report")
        review = state.get("human_review")
        audit_trail = state.get("audit_trail", [])
        sales_records = state.get("sales_records", [])
        rental_records = state.get("rental_records", [])

        # Build provenance matrix
        provenance_matrix = [
            {
                "data_layer": "Subject Property",
                "source": profile.provenance.source if profile and profile.provenance else "Intake User Interface",
                "origin": profile.data_origin.value if profile else "USER-PROVIDED",
                "record_count": 1 if profile else 0,
                "notice": profile.provenance.notice if profile and profile.provenance else "User-provided specifications.",
            },
            {
                "data_layer": "Sales Transactions",
                "source": sales_records[0].provenance.source if sales_records and sales_records[0].provenance else "Synthetic Demonstration Provider v1.0",
                "origin": DataOrigin.SYNTHETIC_DEMONSTRATION_DATA.value,
                "record_count": len(sales_records),
                "notice": SYNTHETIC_NOTICE_TEXT,
            },
            {
                "data_layer": "Rental Listings",
                "source": rental_records[0].provenance.source if rental_records and rental_records[0].provenance else "Synthetic Demonstration Provider v1.0",
                "origin": DataOrigin.SYNTHETIC_DEMONSTRATION_DATA.value,
                "record_count": len(rental_records),
                "notice": SYNTHETIC_NOTICE_TEXT,
            },
            {
                "data_layer": "Submarket Trends",
                "source": "Submarket Trend Provider v1.0",
                "origin": DataOrigin.SYNTHETIC_DEMONSTRATION_DATA.value,
                "record_count": len(market.historical_points) if market and market.historical_points else 0,
                "notice": SYNTHETIC_NOTICE_TEXT,
            },
            {
                "data_layer": "Operational Rent Roll",
                "source": "Rent Roll Provider v1.0",
                "origin": DataOrigin.SYNTHETIC_DEMONSTRATION_DATA.value,
                "record_count": len(rent_units),
                "notice": "Anonymized tenant records (Strict PII Protection); Synthetic demonstration data.",
            },
        ]

        payload: Dict[str, Any] = {
            "report_metadata": {
                "report_id": report_id,
                "generated_at": now_utc,
                "platform_version": self.platform_version,
                "currency": CURRENCY_CODE,
                "currency_symbol": CURRENCY_SYMBOL,
                "locale": "en_IN",
                "system_classification": "Decision-Support System (Non-Autonomous Appraiser)",
                "disclaimers": {
                    "legal_disclaimer": LEGAL_DISCLAIMER_TEXT,
                    "synthetic_notice": SYNTHETIC_NOTICE_TEXT,
                },
            },
            "workflow_execution": {
                "workflow_status": state.get("workflow_status", "UNKNOWN"),
                "step_count": state.get("step_count", 0),
                "max_steps": state.get("max_steps", 15),
                "search_radius_miles": state.get("search_radius_miles", 1.5),
                "evidence_request_count": state.get("evidence_request_count", 0),
                "requires_more_evidence": state.get("requires_more_evidence", False),
                "error_message": state.get("error_message"),
            },
            "property_profile": profile.model_dump(mode="json") if profile else None,
            "valuation": val.model_dump(mode="json") if val else None,
            "rental_pricing": pricing.model_dump(mode="json") if pricing else None,
            "cma_analysis": cma.model_dump(mode="json") if cma else None,
            "comparables": [c.model_dump(mode="json") for c in comps],
            "market_conditions": market.model_dump(mode="json") if market else None,
            "rent_roll_summary": rent_summary.model_dump(mode="json") if rent_summary else None,
            "rent_roll_units": [u.model_dump(mode="json") for u in rent_units],
            "risk_report": risk.model_dump(mode="json") if risk else None,
            "human_review": review.model_dump(mode="json") if review else None,
            "provenance_matrix": provenance_matrix,
            "audit_trail": [entry.model_dump(mode="json") for entry in audit_trail],
        }

        return payload

    def generate_json_export(self, state: AgentWorkflowState, indent: int = 2) -> str:
        """Generate a complete, deterministic, JSON-serialized string of the workflow state."""
        dict_payload = self.generate_json_dict(state)
        return json.dumps(dict_payload, indent=indent, default=str)


# Top-level convenience functions
_DEFAULT_REPORTER = ComplianceDossierReporter()


def generate_markdown_dossier(state: AgentWorkflowState) -> str:
    """Generate executive compliance dossier in Markdown."""
    return _DEFAULT_REPORTER.generate_markdown_dossier(state)


def generate_json_export(state: AgentWorkflowState, indent: int = 2) -> str:
    """Generate structured compliance JSON string."""
    return _DEFAULT_REPORTER.generate_json_export(state, indent=indent)


def generate_json_dict(state: AgentWorkflowState) -> Dict[str, Any]:
    """Generate structured compliance dictionary."""
    return _DEFAULT_REPORTER.generate_json_dict(state)
