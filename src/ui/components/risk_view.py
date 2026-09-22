"""Risk assessment and data quality display component."""

from typing import Optional

import streamlit as st

from src.core.enums import RiskSeverity
from src.core.models import RiskReport


def render_risk_view(risk_report: Optional[RiskReport]) -> None:
    """Render data quality score, risk severity, and itemized warnings."""
    st.markdown("### ⚠️ Risk Assessment & Data Quality Audit")

    if not risk_report:
        st.info("No risk assessment report available.")
        return

    # 1. Overall Severity and Score Cards
    c1, c2, c3 = st.columns(3)

    with c1:
        sev = risk_report.overall_risk_severity
        sev_color = {
            RiskSeverity.LOW: "🟢 LOW",
            RiskSeverity.MEDIUM: "🟡 MEDIUM",
            RiskSeverity.HIGH: "🟠 HIGH",
            RiskSeverity.CRITICAL: "🔴 CRITICAL",
        }.get(sev, sev.value)
        st.metric(label="Overall Risk Severity", value=sev_color)

    with c2:
        st.metric(label="Data Quality Score", value=f"{risk_report.data_quality_score:.1f} / 100")

    with c3:
        flag_count = sum(
            [
                risk_report.is_stale_data,
                risk_report.is_insufficient_comps,
                risk_report.is_missing_rentroll,
                risk_report.is_conflicting_data,
                risk_report.high_variance_warning,
            ]
        )
        st.metric(label="Degraded Factors Flagged", value=f"{flag_count} issue(s)")

    # 2. Summary narrative
    st.info(f"**Audit Findings:** {risk_report.summary}")

    # 3. Itemized Risk Warnings
    if risk_report.items:
        st.markdown("#### 🚨 Itemized Findings & Remediation Steps")
        for item in risk_report.items:
            icon = "🔴" if item.severity == RiskSeverity.CRITICAL else ("🟠" if item.severity == RiskSeverity.HIGH else "🟡")
            with st.expander(f"{icon} [{item.severity.value}] {item.category}: {item.message}", expanded=(item.severity.value in ["HIGH", "CRITICAL"])):
                st.markdown(f"**Affected Fields:** `{', '.join(item.affected_fields)}`")
                st.markdown(f"**Actionable Recommendation:** {item.recommendation}")
    else:
        st.success("✅ Clean Audit: No elevated data quality or valuation risks detected.")
