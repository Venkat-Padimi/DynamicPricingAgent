# AI Real Estate Valuation & Dynamic Pricing Agent (India-First Platform)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 73 Passing](https://img.shields.io/badge/Tests-73%20Passed-brightgreen.svg)]()

> **CRITICAL LEGAL NOTICE:** This platform is an **AI-assisted decision-support system**, NOT an autonomous registered valuer or licensed appraiser under Indian law. All property valuations and rental pricing bands represent analytical guidance. By design, legally binding decisions require explicit **Human-in-the-Loop (HITL)** professional review, validation against authoritative property records (Sub-Registrar / Municipal records), and appropriate professional assessment.
>
> **DATA PROVENANCE NOTICE:** Demonstration data fixtures are mathematically calibrated **synthetic demonstration data** (`Synthetic demonstration data — not real market data`).

---

## 1. Project Overview

The **Automated Valuation & Dynamic Pricing Agent** is an institutional-grade, India-first multi-agent platform engineered for Indian real estate investment trusts (REITs), developers, property asset managers, and commercial real estate operators.

### The Problem It Solves
Valuation in key Indian micro-markets (Hyderabad IT Corridor, Bengaluru Whitefield, Mumbai MMR, Pune Hinjewadi) often suffers from opaque pricing, unstandardized super built-up vs. carpet area definitions, complex lease structures with multi-unit rollover risks, and black-box AI tools that fabricate valuations without verifiable provenance or regulatory alignment.

### The Solution: Multi-Agent Orchestration with Deterministic Guardrails
This platform solves those challenges by combining:
1. **LangGraph Multi-Agent Orchestration:** Specialized agents coordinate property intake, comparable discovery, appraisal adjustments, submarket trend analysis, operational rent-roll audit, dynamic pricing, and risk assessment.
2. **100% Deterministic Financial Core:** Valuation formulas, CMA feature adjustments, rent bands, confidence scores, and risk flags are computed mathematically in Python outside any LLM. The AI never hallucinates or invents market numbers.
3. **India-First Real Estate Standards:** Native Indian numbering system (`₹1.65 Crore`, `₹85 Lakh`, `₹65,000/month`), `BHK` layout configuration, `RERA Carpet Area`, and 6-digit postal `PIN Code` indexing.
4. **Mandatory Human-in-the-Loop Governance:** The pipeline automatically pauses before finalizing recommendations, requiring a designated human reviewer to inspect evidence, adjust overrides, and sign off.
5. **Institutional Compliance Dossier:** Generates full publication-ready Markdown compliance dossiers (`.md`) and structured JSON packages (`.json`) with an immutable event log.

---

## 2. Core Capabilities

- **Automated Property Intake & Normalization:** Validates super built-up area, RERA carpet area, BHK layout, locality, PIN code, age, and condition into a normalized `PropertyProfile`.
- **Multi-Attribute Comparable Similarity:** 7-dimension similarity scoring (distance, square footage, bedrooms/BHK, bathrooms, vintage, condition, amenities).
- **Comparative Market Analysis (CMA) Engine:** Standard appraisal feature adjustments ($Adjusted = CompSalePrice + \sum Adjustments$) calibrated in INR (₹2,500/sq ft area, ₹5,00,000/bed, ₹2,00,000/bath, ₹35,000/yr age, ₹2,50,000/condition step, ₹2,00,000/parking space, ₹1,50,000/amenity).
- **Statistical Outlier Detection:** Dual-method Interquartile Range (IQR) and Z-score outlier filtering.
- **Submarket Trend & Velocity Analysis:** Calculates 24-month sales/rental CAGR, 6-month trailing momentum, gross yields, inventory months, and median days on market (DOM).
- **Operational Rent-Roll & Cliff Analysis:** Physical vs. economic occupancy and vacancy rates, plus a **30 / 60 / 90-day lease expiration cliff ladder**.
- **Tenant PII Protection:** Strict anonymization converting tenant records to pseudonymized cryptographic tokens (`TENANT-XXXX`).
- **Deterministic Valuation Engine:** Multi-component valuation (CMA + Trend + Location + Yield) with dynamic weight renormalization and INR formatting.
- **Dynamic Rental Pricing:** 3-tier rent band `[Floor, Midpoint, Ceiling]` tailored to operational occupancy leverage and lease expiration timing.
- **5-Factor Deterministic Confidence Scoring:** Objective 0–100 point scale (Quantity/Quality, Dispersion, Freshness, Market Stability, Lease Stability) classified into `HIGH`, `MEDIUM`, or `LOW`.
- **Automated Risk & Data Quality Auditing:** 8-category risk scorecard detecting stale records, sparse comps, high variance, and turnover cliffs.
- **Human Review Console:** Interactive Streamlit workflow actions (`Approve`, `Modify` with custom INR overrides, `Reject`, `Request More Evidence`).
- **Interactive Plotly Visualizations:** Scatter plots, CMA waterfall adjustment charts, dual-axis historical trend lines, and expiration cliff bars with Indian currency notation (`Cr`, `L`, `k`, `₹/sq ft`).
- **Compliance Dossier Export:** One-click downloads of complete Executive Markdown dossiers (`.md`) and full JSON payloads (`.json`) with `locale: en_IN` and `currency: INR`.

---

## 3. Architecture & Methodology

- **[System Architecture Documentation](docs/architecture.md):** Detailed guide to the LangGraph node topology, conditional routing, state lifecycle, provenance matrix, and safety guardrails.
- **[Mathematical Methodology Specification](docs/methodology.md):** Full mathematical formulations for similarity scoring, CMA adjustment rates, outlier formulas, valuation weights, rent bands, and confidence scoring.

---

## 4. Installation & Setup

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Operating System: Windows, macOS, or Linux
- **Zero External API Keys Required:** Runs 100% locally and offline out-of-the-box using built-in synthetic fixtures.

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/Venkat-Padimi/DynamicPricingAgent.git
cd DynamicPricingAgent

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 5. Running the Application

Launch the Streamlit executive analytics dashboard:

```bash
streamlit run src/ui/app.py
```

Upon launching, your browser will open to `http://localhost:8501`.

### What to Expect:
- **Dark Slate Institutional Theme:** High-contrast executive dashboard with clear synthetic data disclosure banners.
- **Sidebar Selection:** Switch between Indian demonstration flagship properties (Hyderabad, Bengaluru, Mumbai, Pune, Visakhapatnam) or configure custom property attributes.
- **8 Dedicated Analytics Tabs:**
  1. `📊 Executive Summary`: Valuation estimate (in ₹ Crore / Lakh), valuation range, price per sq ft (`₹/sq ft`), and dynamic rental pricing band (`₹/month`).
  2. `🏘️ Comparables (CMA)`: Interactive comps scatter plot and individual comp cards with similarity badges and outlier flags.
  3. `📈 Market Trends`: 24-month historical trend line chart, annualized sales/rental CAGR, and momentum velocity.
  4. `🏢 Lease & Rent Roll`: Physical vs. economic occupancy gauges, 30/60/90-day cliff ladder, and anonymized unit schedules.
  5. `⚠️ Risk & Data Quality`: Categorized risk scorecard with severity badges.
  6. `🧑‍⚖️ Human Review Console`: Mandatory review gate with interactive decision triggers.
  7. `📜 Agent Audit Trace`: Chronological multi-agent execution event log with millisecond latencies.
  8. `📥 Dossier & Export`: Live preview and one-click downloads for Markdown dossiers and structured JSON payloads.

---

## 6. Running Tests

The test suite runs 100% offline without network calls or external dependencies:

```bash
# Run complete test suite (73 tests)
python -m pytest tests/ -v

# Run targeted Indian localization tests
python -m pytest tests/unit/test_indian_localization.py -v

# Run targeted CMA and Valuation test suites
python -m pytest tests/unit/test_cma.py -v
python -m pytest tests/unit/test_valuation_and_pricing.py -v
```

---

## 7. Interactive Demonstration Workflow

1. **Launch Dashboard:** Run `streamlit run src/ui/app.py`.
2. **Select Demo Asset:** Select *"Hyderabad HITEC City / Gachibowli (PROP-HYD-001)"* from the sidebar.
3. **Execute Analysis:** Click **🚀 Run Analysis**. The LangGraph supervisor executes the multi-agent pipeline and pauses at the Human Review stage.
4. **Inspect Valuation & Pricing:** View the deterministic estimate (`₹1.65 Crore`), low/high bounds, and recommended rent band (`₹60,000` - `₹70,000/month`).
5. **Inspect CMA Waterfall:** Navigate to `🏘️ Comparables (CMA)` to view the step-by-step appraisal feature adjustment waterfall in INR.
6. **Inspect Lease Cliff Ladder:** Navigate to `🏢 Lease & Rent Roll` to check the 30/60/90-day expiration schedule.
7. **Perform Human Review:** Navigate to `🧑‍⚖️ Human Review Console`:
   - Choose **Modify Recommendation**.
   - Input custom valuation: `₹1,75,00,000` (`₹1.75 Crore`).
   - Input custom rent: `₹68,000/month`.
   - Provide justification: *"Upward premium applied for high-floor corner unit and proximity to Cyber Towers."*
   - Click **Submit Human Decision**.
8. **Export Final Compliance Dossier:**
   - Navigate to `📥 Dossier & Export`.
   - Click **⬇️ Download Executive Dossier (.md)** to download the finalized compliance dossier.
   - Click **⬇️ Download Structured Data (.json)** to export the full machine-readable JSON archive.

---

## 8. Data Integrity, Provenance & Privacy

- **No Hallucinated Financials:** All calculations are performed by deterministic Python engines. The LLM is never permitted to invent prices or statistical metrics.
- **Clear Provenance Matrix:** Every dataset consulted carries an explicit origin tag (`SYNTHETIC DEMONSTRATION DATA`, `VERIFIED MARKET DATA`, `USER-PROVIDED PROPERTY DATA`).
- **Strict Tenant Privacy (Zero PII):** All names, phone numbers, and contact details are removed; tenant IDs are anonymized tokens (`TENANT-89F1`).
- **Immutable Multi-Agent Audit Trail:** Every step records timestamp, agent name, action, latency, sources consulted, and warnings issued.

---

## 9. Mandatory Disclaimer

> Decision-Support Notice: This AI-assisted valuation is intended for research and decision-support purposes only. It is NOT a legally binding appraisal, registered valuation, or professional assessment under Indian law. Human review, verification against authoritative property records (Sub-Registrar / Municipal records), and appropriate professional assessment are required before financial, legal, lending, or investment decisions.
