# Automated Valuation & Dynamic Pricing Agent - Walkthrough

## Phase 1: Architecture, Core Domain Models & State Machine

### What Was Built
- **Core Enums ([enums.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/enums.py))**:
  - `PropertyType`: SingleFamily, Condo, Townhouse, MultiFamily, Commercial
  - `PropertyCondition`: Poor, Fair, Good, Excellent, LuxuryRenovated
  - `DataOrigin`: VERIFIED MARKET DATA, USER-PROVIDED PROPERTY DATA, SYNTHETIC DEMONSTRATION DATA, MODEL PREDICTIONS, AGENT INTERPRETATIONS
  - `ConfidenceLevel`: HIGH, MEDIUM, LOW
  - `ReviewStatus`: PENDING, APPROVED, MODIFIED, REJECTED, EVIDENCE_REQUESTED
  - `RiskSeverity`: LOW, MEDIUM, HIGH, CRITICAL
  - `LeaseStatus`: OCCUPIED, VACANT, NOTICE_GIVEN, RENEWAL_PENDING
  - `MarketTrendDirection`: APPRECIATING, STABLE, SOFTENING, DECLINING

- **Domain Models ([models.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/models.py))**:
  - `ProvenanceMetadata`: Enforces non-fabrication guarantees and mandatory synthetic demonstration notice.
  - `PropertyProfile`: Subject property attributes, dimensions, condition, age, and amenities.
  - `MarketRecord`: Comparable transactions with sale/rent PSF calculation and strict origin classification.
  - `FeatureAdjustment` & `ComparableProperty`: CMA line-item adjustment tracking.
  - `CMAAnalysis`: Synthesis with distribution statistics and outlier pruning.
  - `SubmarketMetricPoint` & `MarketConditions`: Factual statistics strictly separated from agent interpretations.
  - `RentRollUnit` & `RentRollSummary`: Unit-level rent roll with pseudonymized tenant IDs (zero PII exposure).
  - `ValuationResult` & `ValuationComponentBreakdown`: Deterministic multi-component valuation output with embedded mandatory legal disclaimers.
  - `RentalPricingResult` & `RentalPricingBreakdown`: Recommended rental ranges, midpoints, and rent gaps.
  - `RiskReport` & `RiskItem`: Categorized data quality and variance alerts.
  - `HumanReviewDecision`: Complete record of reviewer ID, role, action, overrides, and notes.
  - `AuditEntry`: Immutable audit trail for every agent action.

- **Workflow State ([state.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/state.py))**:
  - `AgentWorkflowState`: TypedDict state model for the LangGraph multi-agent supervisor and workers.

---

## Phase 2: Market & Comparable Data Layer (Provider Adapter + Synthetic Fixtures)

### What Was Built
- **Provider Abstractions ([base.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/data/providers/base.py))**:
  - `BaseMarketDataProvider`: Interface for sales comps, rental comps, and historical market trend queries.
  - `BaseRentRollProvider`: Interface for unit-level operational rent rolls and occupancy summaries.
- **Synthetic Demonstrative Fixtures ([fixtures/](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/data/fixtures/))**:
  - `sales_comps.json`, `rental_comps.json`, `rent_rolls.json`, `market_trends.json` with explicit provenance tags.
- **Synthetic Provider Implementation ([synthetic_provider.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/data/providers/synthetic_provider.py))**:
  - High-performance local querying, geographic filtering, and rent roll operational calculations.

---

## Phase 3: Property Intake & Comparable Selection / CMA Engine

### What Was Built
- **Property Intake Engine ([intake_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/intake_engine.py))**: Normalizes and validates subject property specs.
- **Multi-Attribute Similarity Scoring ([comparable_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/comparable_engine.py))**: Distance, sqft, beds, baths, age, condition, amenities.
- **Appraisal Feature Adjustments ([comparable_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/comparable_engine.py))**: Standard appraisal directionality (adjusting comp to subject).
- **Statistical Outlier Detection ([comparable_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/comparable_engine.py))**: Dual-method IQR and Z-score tests.
- **CMA Synthesis ([comparable_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/comparable_engine.py))**: Top-comps ranking with plain-language selection rationales.

---

## Phase 4: Lease & Rent-Roll Analysis + Market Conditions

### What Was Built
- **Lease Analysis Engine ([lease_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/lease_engine.py))**: Occupancy, vacancy, gross potential rent, in-place rent, rent gap, and 30/60/90-day expiration cliff ladder. Eliminates tenant PII.
- **Market Conditions Engine ([market_conditions_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/market_conditions_engine.py))**: Computes annualized sales and rent CAGR, 6-month momentum, gross yields, inventory, and DOM. Separates historical facts from qualitative commentary.

---

## Phase 5: Deterministic Valuation & Dynamic Pricing Engines

### What Was Built
- **Deterministic Valuation Engine ([valuation_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/valuation_engine.py))**: Multi-component formula (CMA + Trend + Location + Income Capitalization) with dynamic weight renormalization and low/high range logic.
- **Deterministic Dynamic Pricing Engine ([pricing_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/pricing_engine.py))**: 3-tier recommended rent range [Floor, Midpoint, Ceiling] and in-place vs. market rent gap analysis.
- **Deterministic Confidence Scoring Engine ([scoring.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/scoring.py))**: 0–100 point scoring system mapped to `HIGH`, `MEDIUM`, and `LOW` tiers.

---

## Phase 6: Risk Assessment, Data Quality & Human Review Logic

### What Was Built
- **Risk Assessment & Data Quality Engine ([risk_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/risk_engine.py))**: Audits 8 risk categories, computes `data_quality_score`, and assigns `overall_risk_severity`.
- **Human Review Engine ([human_review_engine.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/core/human_review_engine.py))**: Enforces mandatory human approval controls (`APPROVE`, `MODIFY`, `REJECT`, `REQUEST_MORE_EVIDENCE`).

---

## Phase 7: LangGraph Multi-Agent Orchestration & Supervisor

### What Was Built
- **Specialized Agent Nodes ([nodes.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/workflow/nodes.py))**:
  - `property_intake_node`: Ingests and normalizes subject property data.
  - `market_data_node`: Retrieves sales and rental transactions with provenance.
  - `cma_node`: Evaluates similarity, feature adjustments, and outlier flags. Auto-expands radius if comps $< 3$.
  - `market_conditions_node`: Computes 24-month trends and momentum.
  - `lease_rentroll_node`: Processes operational unit schedule and expiration cliff.
  - `valuation_node`: Calculates deterministic valuation breakdown and confidence.
  - `dynamic_pricing_node`: Computes rent floor/midpoint/ceiling and gap analysis.
  - `risk_quality_node`: Runs automated risk auditing and data quality scoring.
  - `human_review_node`: Enforces mandatory Human-in-the-Loop review gate, pausing workflow until human reviewer acts.
  - `final_report_node`: Seals final decision, records audit trail, and issues completion status.

- **Conditional Routing & Safety ([routing.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/workflow/routing.py))**:
  - `route_after_cma`: Automatically widens comparable search radius when comp count $< 3$ (up to 4.5 mi limit) and loops back to market data acquisition.
  - `route_after_human_review`:
    - `APPROVE` / `MODIFY` $\to$ `final_report` (completion).
    - `REJECT` $\to$ `final_report` (halts decision finalization).
    - `REQUEST_MORE_EVIDENCE` $\to$ loops back to `market_data` with expanded search parameters.
    - Loop protection: Enforces a maximum step budget of 15 and max 3 evidence request cycles.

- **Workflow Compilation & Execution Helpers ([graph.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/workflow/graph.py))**:
  - `build_workflow_graph()`: Constructs and compiles `StateGraph(AgentWorkflowState)`.
  - `run_pipeline()`: Executes workflow synchronously to the human review gate.
  - `submit_human_decision()`: Injects reviewer decision and finalizes workflow.

- **Comprehensive Audit Trail**:
  - Every agent records step index, timestamp, action, inputs summary, outputs summary, sources consulted, execution latency in milliseconds, and issued warnings into `state["audit_trail"]`.

---

## Phase 8: Streamlit Executive Analytics Dashboard & Visualizations

### What Was Built
- **Executive Dashboard Application ([app.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/ui/app.py))**:
  - High-performance, executive dark theme (`#0f172a` slate palette) with responsive typography and metrics cards.
  - Two-phase execution loop: Runs workflow up to Human Review gate, displays interactive tabs, captures user review action (`APPROVE`, `MODIFY`, `REJECT`, `REQUEST_MORE_EVIDENCE`), and finalizes workflow.
  - Strictly consumes deterministic engine outputs without duplicating business logic.

- **Plotly Visualizations Suite ([visualizations.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/ui/visualizations.py))**:
  - `plot_valuation_weights_donut`: Donut chart of deterministic component weights with center value readout.
  - `plot_confidence_radar`: 5-dimension radar chart showing comp quality, variance, data freshness, market stability, and lease stability scores.
  - `plot_rental_pricing_band`: Bullet/range visualization with Floor, Recommended Midpoint, Ceiling, and current in-place rent marker.
  - `plot_comps_scatter`: Scatter plot of comps (sale price vs. square footage) sized by similarity score, with subject property highlighted.
  - `plot_cma_waterfall`: Step-by-step appraisal adjustment waterfall from base sale price to final adjusted price.
  - `plot_historical_psf_trend`: Dual-axis 24-month trend chart for sales price/sqft and rental rate/sqft.
  - `plot_lease_cliff_ladder`: Color-coded expiration ladder for 30/60/90-day and >90-day lease exposures.

- **Modular UI Component Panels ([components/](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/ui/components/))**:
  - `property_selector.py`: Pre-loaded demo properties (Austin, Seattle, Miami) + custom property intake form with explicit provenance labels.
  - `valuation_view.py`: Estimated valuation, low/high range, price/sqft, confidence gauge, weights breakdown, and mandatory disclaimer banners.
  - `pricing_view.py`: Recommended monthly rent, 3-tier price band, in-place rent comparison, and positioning strategy.
  - `comps_view.py`: Scatter plot and detailed comp cards with similarity badges, adjustment totals, and outlier flags.
  - `cma_view.py`: Interactive comp selector for detailed adjustment waterfall breakdown and adjustment formulas.
  - `trends_view.py`: 24-month historical trend line chart, annualized sales/rental CAGR, 6-month momentum badges, and market velocity metrics (DOM, inventory).
  - `rentroll_view.py`: Physical vs. economic occupancy metrics, 30/60/90-day expiration cliff ladder, unit schedule table with PII tokens, and potential rent gap.
  - `risk_view.py`: Categorized risk and data quality audit items with color-coded severity badges (Critical, High, Medium, Low).
  - `human_review_view.py`: HITL review console with 4 discrete actions (`Approve`, `Modify` with inputs and justification, `Reject` with reason, `Request More Evidence` with parameters).
  - `audit_view.py`: Full chronological execution event log detailing agent nodes, execution latencies, input/output summaries, and warnings.

---

## Phase 9: Reporting, Export & Compliance Dossier

### What Was Built
- **Compliance Dossier Reporter ([reporter.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/reporting/reporter.py))**:
  - `ComplianceDossierReporter` class with module-level convenience functions (`generate_markdown_dossier`, `generate_json_export`, `generate_json_dict`).
  - **Executive Markdown Compliance Dossier (`.md`)**:
    1. **Document Header & Metadata**: Asset identifier, address, generation timestamp (UTC), platform version, workflow status.
    2. **Mandatory Disclaimers Banner**: Legal decision-support disclaimer (`LEGAL_DISCLAIMER_TEXT`), synthetic data demonstration notice (`SYNTHETIC_NOTICE_TEXT`), non-autonomous appraiser classification.
    3. **Executive Summary**: Deterministic valuation ($ value, low/high range, $/sqft, confidence level & score, component weights breakdown), dynamic rental pricing band (Floor, Midpoint, Ceiling, in-place rent gap, positioning strategy).
    4. **Subject Property Overview**: Dimensions, age, condition, amenities, parking, occupancy rate.
    5. **Data Provenance Matrix**: Source name, origin class (`SYNTHETIC DEMONSTRATION DATA`, `USER-PROVIDED`), records queried, integrity notice.
    6. **Comparative Market Analysis (CMA)**: Selection rationale, summary statistics, comps table with distance, similarity, sale date, net adjustments, outlier flags, and line-item feature adjustment breakdown confirming appraisal directionality ($Adjusted = CompSalePrice + \sum Adjustments$).
    7. **Submarket Conditions & Historical Trends**: 24-month sales CAGR, rental CAGR, 6-month price momentum, gross yield, days on market (DOM), inventory, factual summary vs. agent forward interpretation.
    8. **Operational Rent Roll & Expiration Cliff Ladder**: Physical/economic occupancy & vacancy, gross potential rent, in-place rent, average rent PSF, 30/60/90-day cliff ladder, and pseudonymized unit rent schedule (`TENANT-xxx`, zero PII).
    9. **Risk & Data Quality Scorecard**: Overall severity badge, composite data quality score (0–100), audit flags table with diagnostic finding and mitigating recommendation.
    10. **Human-in-the-Loop Review Sign-Off**: Review status badge (`APPROVED`, `MODIFIED`, `REJECTED`, `EVIDENCE_REQUESTED`, `PENDING`), reviewer ID, name, role, timestamp, justification notes, overrides applied, and formal reviewer legal attestation statement.
    11. **Multi-Agent Audit Trail**: Step-by-step chronological log with timestamps, agent nodes, actions, execution latency in milliseconds, output summaries, and warnings.
    12. **Closing Legal Attestation & Disclaimers**.
  - **Structured JSON Export (`.json`)**:
    - Machine-readable, deterministic payload containing `report_metadata`, `workflow_execution`, `property_profile`, `valuation`, `rental_pricing`, `cma_analysis`, `comparables`, `market_conditions`, `rent_roll_summary`, `rent_roll_units` (strictly pseudonymized), `risk_report`, `human_review`, `provenance_matrix`, and `audit_trail`.

- **Streamlit Dashboard Export Integration ([export_view.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/ui/components/export_view.py)) & ([app.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/src/ui/app.py))**:
  - Integrated 8th tab: `"📥 Dossier & Export"` in the dashboard.
  - One-click download buttons:
    - `⬇️ Download Executive Dossier (.md)`
    - `⬇️ Download Structured Data (.json)`
  - Dynamic file naming incorporating property ID and reviewer status.
  - Interactive In-App Previews for both Markdown and JSON payloads.

---

## Phase 10: Full Test Suite, Documentation & Final Polish

### What Was Built
- **Comprehensive System Architecture Documentation ([docs/architecture.md](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/docs/architecture.md))**:
  - Complete architectural blueprint documenting the LangGraph multi-agent topology, supervisor/orchestration flow, 10 specialized nodes, conditional routing, state lifecycle, deterministic computational boundaries, provenance matrix, and presentation layer.
  - Includes Mermaid workflow sequence and topology diagrams.
- **Mathematical & Deterministic Methodology Specification ([docs/methodology.md](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/docs/methodology.md))**:
  - Rigorous mathematical specifications for similarity distance functions, appraisal adjustment rates, IQR/Z-score outlier thresholds, multi-component valuation formulas, dynamic rental pricing bands, 30/60/90-day cliff ladders, CAGR/momentum equations, and the 5-factor confidence scoring engine.
- **Production-Ready Operational Guide ([README.md](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/README.md))**:
  - Public repository README detailing capabilities, zero-API-key local setup, virtual environment commands, running the Streamlit app, test suite execution, step-by-step interactive demonstration walkthrough, provenance safeguards, and mandatory decision-support disclaimers.
- **Root Project Dependency Manifest ([requirements.txt](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/requirements.txt))**:
  - Pinned core dependencies covering LangGraph, Pydantic, Streamlit, Plotly, Pandas, and Pytest.
- **End-to-End System Integration Test Suite ([tests/integration/test_end_to_end_integration.py](file:///c:/Users/Venkat/Desktop/Sat%20Datta%20Projects/DynamicPricingAgent/tests/integration/test_end_to_end_integration.py))**:
  - 3 high-coverage end-to-end integration tests validating:
    1. Complete property intake -> market data -> CMA -> trends -> lease -> valuation -> dynamic pricing -> risk audit -> human review approval -> compliance dossier generation.
    2. Reviewer modification override workflow with custom valuation/rent overrides.
    3. Multi-run deterministic reproducibility verifying identical bit-for-bit financial outputs across consecutive pipeline runs.

---

## Final Regression Verification Results

Ran: `python -m pytest tests/ -v`

```
tests/integration/test_end_to_end_integration.py::test_full_pipeline_end_to_end_lifecycle PASSED [  1%]
tests/integration/test_end_to_end_integration.py::test_pipeline_modification_lifecycle PASSED [  3%]
tests/integration/test_end_to_end_integration.py::test_pipeline_determinism_across_multiple_runs PASSED [  4%]
tests/unit/test_cma.py::test_property_intake_normalization PASSED        [  6%]
tests/unit/test_cma.py::test_similarity_calculator_identical_vs_dissimilar PASSED [  7%]
tests/unit/test_cma.py::test_similarity_custom_weights PASSED            [  9%]
tests/unit/test_cma.py::test_appraisal_adjustments_rule PASSED           [ 10%]
tests/unit/test_cma.py::test_outlier_detection_iqr_and_zscore PASSED     [ 12%]
tests/unit/test_cma.py::test_cma_engine_end_to_end_with_synthetic_records PASSED [ 14%]
tests/unit/test_cma.py::test_cma_engine_no_matching_comps_graceful_handling PASSED [ 15%]
tests/unit/test_lease_and_market.py::test_lease_analysis_engine_metrics PASSED [ 17%]
tests/unit/test_lease_and_market.py::test_lease_expiration_cliff_analysis PASSED [ 18%]
tests/unit/test_lease_and_market.py::test_tenant_pii_strict_protection PASSED [ 20%]
tests/unit/test_lease_and_market.py::test_lease_fact_vs_interpretation_separation PASSED [ 21%]
tests/unit/test_lease_and_market.py::test_market_conditions_cagr_and_momentum PASSED [ 23%]
tests/unit/test_lease_and_market.py::test_market_conditions_edge_cases PASSED [ 25%]
tests/unit/test_lease_and_market.py::test_deterministic_reproducibility PASSED [ 26%]
tests/unit/test_models.py::test_provenance_enforces_synthetic_label PASSED [ 28%]
tests/unit/test_models.py::test_property_profile_validation PASSED       [ 29%]
tests/unit/test_models.py::test_market_record_psf_calculation PASSED     [ 31%]
tests/unit/test_models.py::test_cma_adjustment_model PASSED              [ 32%]
tests/unit/test_models.py::test_rent_roll_pii_protection PASSED          [ 34%]
tests/unit/test_models.py::test_valuation_result_contains_mandatory_disclaimer PASSED [ 35%]
tests/unit/test_models.py::test_human_review_decision_tracking PASSED    [ 37%]
tests/unit/test_providers.py::test_provider_provenance_integrity PASSED  [ 39%]
tests/unit/test_sales_comps_filtering_by_distance_and_sqft PASSED        [ 40%]
tests/unit/test_providers.py::test_rental_comps_query PASSED             [ 42%]
tests/unit/test_providers.py::test_market_trends_retrieval PASSED        [ 43%]
tests/unit/test_providers.py::test_rent_roll_units_and_anonymization PASSED [ 45%]
tests/unit/test_providers.py::test_rent_roll_summary_calculations PASSED [ 46%]
tests/unit/test_providers.py::test_rent_roll_missing_property PASSED     [ 48%]
tests/unit/test_reporting.py::test_markdown_dossier_required_sections_and_disclaimers PASSED [ 50%]
tests/unit/test_reporting.py::test_json_export_structure_and_serialization PASSED [ 51%]
tests/unit/test_reporting.py::test_human_review_approval_decision_preservation PASSED [ 53%]
tests/unit/test_reporting.py::test_human_review_modify_decision_with_overrides PASSED [ 54%]
tests/unit/test_reporting.py::test_human_review_reject_decision PASSED   [ 56%]
tests/unit/test_reporting.py::test_deterministic_reproducibility PASSED  [ 57%]
tests/unit/test_reporting.py::test_graceful_missing_and_partial_data_handling PASSED [ 59%]
tests/unit/test_risk_and_review.py::test_risk_quality_engine_insufficient_comps PASSED [ 60%]
tests/unit/test_risk_and_review.py::test_risk_quality_engine_stale_data_and_variance PASSED [ 62%]
tests/unit/test_human_review_approve PASSED                             [ 64%]
tests/unit/test_human_review_modify_success PASSED                      [ 65%]
tests/unit/test_human_review_modify_validation_enforcement PASSED       [ 67%]
tests/unit/test_human_review_reject PASSED                              [ 68%]
tests/unit/test_human_review_request_more_evidence PASSED                [ 70%]
tests/unit/test_ui_and_visualizations.py::test_demo_properties_structure PASSED [ 71%]
tests/unit/test_ui_and_visualizations.py::test_plot_comps_scatter PASSED [ 73%]
tests/unit/test_ui_and_visualizations.py::test_plot_cma_waterfall PASSED [ 75%]
tests/unit/test_ui_and_visualizations.py::test_plot_historical_psf_trend PASSED [ 76%]
tests/unit/test_ui_and_visualizations.py::test_plot_lease_cliff_ladder PASSED [ 78%]
tests/unit/test_ui_and_visualizations.py::test_dashboard_full_lifecycle_state_flow PASSED [ 79%]
tests/unit/test_valuation_and_pricing.py::test_deterministic_valuation_with_cma_and_income PASSED [ 81%]
tests/unit/test_valuation_and_pricing.py::test_valuation_missing_data_fallbacks PASSED [ 82%]
tests/unit/test_valuation_and_pricing.py::test_dynamic_rental_pricing_floor_midpoint_ceiling PASSED [ 84%]
tests/unit/test_valuation_and_pricing.py::test_dynamic_pricing_missing_rentals_fallback PASSED [ 85%]
tests/unit/test_confidence_scoring_tiers PASSED                          [ 87%]
tests/unit/test_valuation_and_pricing.py::test_deterministic_reproducibility_valuation PASSED [ 89%]
tests/unit/test_workflow.py::test_end_to_end_pipeline_pauses_at_human_review PASSED [ 90%]
tests/unit/test_workflow.py::test_human_review_approval_flow PASSED      [ 92%]
tests/unit/test_workflow.py::test_human_review_modify_flow PASSED        [ 93%]
tests/unit/test_workflow.py::test_human_review_reject_flow PASSED        [ 95%]
tests/unit/test_workflow.py::test_human_review_request_more_evidence_flow PASSED [ 96%]
tests/unit/test_workflow.py::test_cma_radius_expansion_routing PASSED    [ 98%]
tests/unit/test_workflow.py::test_step_budget_exhaustion_in_human_review_loop PASSED [100%]

============================= 64 passed in 1.86s ==============================
```

---

## Known Limitations
1. **Demonstration Data Fixtures**: All market comps, rents, and submarket trend data are mathematically calibrated synthetic fixtures labeled with the mandatory notice: `"Synthetic demonstration data — not real market data."`
2. **Export File Formats**: Native exports target GitHub Flavored Markdown (`.md`) and raw serialized JSON (`.json`). Native PDF generation is omitted to prevent heavy C-runtime library dependencies (Cairo/Pango) on Windows environments.
