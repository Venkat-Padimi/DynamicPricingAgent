"""Agent audit trail timeline and provenance inspection component."""

from typing import List

import pandas as pd
import streamlit as st

from src.core.models import AuditEntry


def render_audit_view(audit_trail: List[AuditEntry]) -> None:
    """Render chronological multi-agent execution audit trail with latencies and provenance."""
    st.markdown("### 📜 Agent Audit Trail & Provenance Matrix")

    if not audit_trail:
        st.info("No audit trail entries recorded.")
        return

    # 1. Summary Metrics Row
    total_steps = len(audit_trail)
    total_latency_ms = sum(e.execution_time_ms for e in audit_trail)
    total_warnings = sum(len(e.warnings_issued) for e in audit_trail)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Workflow Steps", f"{total_steps} steps")
    with c2:
        st.metric("Total Execution Latency", f"{total_latency_ms:.1f} ms")
    with c3:
        st.metric("Total Warnings Logged", f"{total_warnings} warning(s)")

    # 2. Chronological Timeline Table
    rows = []
    for e in audit_trail:
        rows.append(
            {
                "Step #": e.step_index,
                "Agent": e.agent_name,
                "Action": e.action,
                "Latency": f"{e.execution_time_ms:.1f} ms",
                "Timestamp (UTC)": e.timestamp.strftime("%H:%M:%S.%f")[:-3],
                "Sources Consulted": ", ".join(e.sources_consulted) if e.sources_consulted else "Internal Model",
                "Warnings": len(e.warnings_issued),
                "Decision / Status": e.decision or "Success",
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 3. Detailed Step Inspector
    st.markdown("#### 🔬 Inspect Step Inputs & Outputs")
    for e in audit_trail:
        with st.expander(f"Step {e.step_index}: {e.agent_name} — {e.action} ({e.execution_time_ms:.1f} ms)"):
            c_in, c_out = st.columns(2)
            with c_in:
                st.markdown("**Inputs Summary:**")
                st.info(e.inputs_summary)
            with c_out:
                st.markdown("**Outputs Summary:**")
                st.success(e.outputs_summary)

            if e.sources_consulted:
                st.markdown(f"**Data Sources Consulted:** `{', '.join(e.sources_consulted)}`")

            if e.warnings_issued:
                st.markdown("**Warnings Issued:**")
                for w in e.warnings_issued:
                    st.warning(f"⚠️ {w}")
