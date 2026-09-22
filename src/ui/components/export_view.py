"""Streamlit component for generating and downloading the Executive Compliance Dossier and Structured JSON."""

import json
from typing import Optional

import streamlit as st

from src.core.state import AgentWorkflowState
from src.reporting.reporter import generate_json_export, generate_markdown_dossier


def render_export_view(state: Optional[AgentWorkflowState]):
    """Render the compliance dossier export panel and download controls."""
    st.subheader("📑 Institutional Compliance Dossier & Data Export")
    st.caption(
        "Generate and export comprehensive, auditable investment committee packages including valuation, "
        "dynamic rental pricing, CMA adjustments, provenance matrix, human review sign-off, and execution logs."
    )

    if not state or not state.get("property_profile"):
        st.info("ℹ️ Execute the multi-agent analysis pipeline to generate exportable compliance dossiers.")
        return

    profile = state["property_profile"]
    prop_id = profile.property_id
    workflow_status = state.get("workflow_status", "PENDING")
    review = state.get("human_review")
    status_suffix = review.status.value.lower() if review else "pending_review"

    # Generate current dossier and JSON from live state
    dossier_md = generate_markdown_dossier(state)
    dossier_json = generate_json_export(state, indent=2)

    # 1. Action Cards / Download Buttons
    st.markdown("#### 📥 One-Click Dossier Export")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style="background-color: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #3b82f6; margin-bottom: 12px;">
                <h4 style="color: #60a5fa; margin-top: 0;">📄 Executive Compliance Dossier (.md)</h4>
                <p style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">
                    Comprehensive markdown dossier containing executive valuation summary, dynamic pricing bands, 
                    full CMA adjustments table, rent-roll cliff ladder, risk scorecard, human sign-off block, and mandatory disclaimers.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        md_filename = f"compliance_dossier_{prop_id}_{status_suffix}.md"
        st.download_button(
            label="⬇️ Download Executive Dossier (.md)",
            data=dossier_md,
            file_name=md_filename,
            mime="text/markdown",
            type="primary",
            use_container_width=True,
            key="btn_download_md",
        )

    with col2:
        st.markdown(
            """
            <div style="background-color: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #10b981; margin-bottom: 12px;">
                <h4 style="color: #34d399; margin-top: 0;">💾 Structured Compliance Data (.json)</h4>
                <p style="color: #94a3b8; font-size: 13px; margin-bottom: 12px;">
                    Complete machine-readable JSON payload containing normalized property specifications, comparable records, 
                    deterministic weights, audit trail, provenance matrix, and governance decision metadata.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        json_filename = f"valuation_pricing_payload_{prop_id}_{status_suffix}.json"
        st.download_button(
            label="⬇️ Download Structured Data (.json)",
            data=dossier_json,
            file_name=json_filename,
            mime="application/json",
            type="secondary",
            use_container_width=True,
            key="btn_download_json",
        )

    st.divider()

    # 2. In-App Preview Section
    preview_mode = st.radio(
        "Preview Export Artifact:",
        ["Executive Markdown Dossier Preview", "Structured JSON Schema & Content Preview"],
        horizontal=True,
    )

    if preview_mode == "Executive Markdown Dossier Preview":
        st.markdown("##### 📄 Live Dossier Document Preview")
        with st.container(height=600):
            st.markdown(dossier_md)
    else:
        st.markdown("##### 💾 Structured JSON Preview")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("JSON Payload Size", f"{len(dossier_json.encode('utf-8')) / 1024:.1f} KB")
        col_m2.metric("Audit Trail Events", f"{len(state.get('audit_trail', []))} steps")
        col_m3.metric("Comps Evaluated", f"{len(state.get('comparables', []))} comps")

        with st.container(height=500):
            st.json(json.loads(dossier_json))
