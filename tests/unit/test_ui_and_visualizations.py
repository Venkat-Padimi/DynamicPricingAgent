"""Unit tests for UI components, Plotly visualizations, and dashboard state handling."""

import pytest
import plotly.graph_objects as go

from src.core.enums import PropertyCondition, PropertyType, ReviewStatus
from src.core.human_review_engine import HumanReviewEngine
from src.core.models import (
    ComparableProperty,
    FeatureAdjustment,
    MarketRecord,
    PropertyProfile,
    ProvenanceMetadata,
    RentRollSummary,
)
from src.ui.components.property_selector import DEMO_PROPERTIES
from src.ui.visualizations import (
    plot_cma_waterfall,
    plot_comps_scatter,
    plot_historical_psf_trend,
    plot_lease_cliff_ladder,
)
from src.workflow.graph import run_pipeline, submit_human_decision


@pytest.fixture
def sample_comparable():
    prov = ProvenanceMetadata(source="Synthetic Demo")
    rec = MarketRecord(
        record_id="COMP-001",
        address="1210 Colorado St",
        city="Austin",
        state="TX",
        zip_code="78701",
        property_type=PropertyType.CONDO,
        transaction_date="2025-11-01",
        sale_price=580000.0,
        sqft=1150.0,
        bedrooms=2,
        bathrooms=2.0,
        year_built=2019,
        distance_miles=0.2,
        provenance=prov,
    )
    adj = FeatureAdjustment(
        feature_name="Square Footage",
        subject_value="1,200 sqft",
        comp_value="1,150 sqft",
        raw_difference=50.0,
        adjustment_rate=150.0,
        adjustment_amount=7500.0,
        rationale="Subject is 50 sqft larger",
    )
    return ComparableProperty(
        record=rec,
        similarity_score=0.92,
        adjustments=[adj],
        total_net_adjustment=7500.0,
        adjusted_price=587500.0,
        adjusted_price_psf=489.58,
        selection_rationale="Close proximity and identical floorplan",
        is_outlier=False,
    )


def test_demo_properties_structure():
    """Verify demo properties dictionary contains Austin, Seattle, and Miami fixtures."""
    assert len(DEMO_PROPERTIES) >= 3
    cities = [d["city"] for d in DEMO_PROPERTIES.values()]
    assert "Austin" in cities
    assert "Seattle" in cities
    assert "Miami" in cities

    for name, prop in DEMO_PROPERTIES.items():
        assert prop["sqft"] > 0
        assert prop["bedrooms"] >= 1
        assert prop["bathrooms"] >= 1.0
        assert prop["year_built"] >= 2000
        assert "Synthetic" in prop.get("source", "") or "Demonstration" in prop.get("source", "")


def test_plot_comps_scatter(sample_comparable):
    """Verify Plotly scatter plot generates correctly with subject and comp markers."""
    fig = plot_comps_scatter(
        comparables=[sample_comparable],
        subject_sqft=1200.0,
        subject_estimated_val=590000.0,
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2  # Comps trace and subject marker trace

    # Empty list handling
    fig_empty = plot_comps_scatter(comparables=[], subject_sqft=1200.0)
    assert isinstance(fig_empty, go.Figure)
    assert len(fig_empty.layout.annotations) > 0


def test_plot_cma_waterfall(sample_comparable):
    """Verify CMA adjustment waterfall chart generation."""
    fig = plot_cma_waterfall(sample_comparable)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    waterfall_trace = fig.data[0]
    assert waterfall_trace.type == "waterfall"
    assert "Base Sale Price" in list(waterfall_trace.x)
    assert "Adjusted Price" in list(waterfall_trace.x)


def test_plot_historical_psf_trend():
    """Verify historical PSF dual-axis line chart generation."""
    from src.data.providers.synthetic_provider import SyntheticMarketDataProvider
    provider = SyntheticMarketDataProvider()
    trends = provider.get_market_trends("Austin-Downtown")

    fig = plot_historical_psf_trend(trends)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # Sales PSF line and Rental PSF line

    # Missing trend data handling
    fig_none = plot_historical_psf_trend(None)
    assert isinstance(fig_none, go.Figure)
    assert len(fig_none.layout.annotations) > 0


def test_plot_lease_cliff_ladder():
    """Verify 30/60/90-day expiration cliff ladder bar chart generation."""
    summary = RentRollSummary(
        property_id="PROP-TEST",
        total_units=10,
        occupied_units=8,
        physical_occupancy_rate=0.80,
        gross_potential_monthly_rent=25000.0,
        current_in_place_monthly_rent=20000.0,
        avg_rent_per_unit=2500.0,
        avg_rent_psf=2.80,
        expiring_within_30_days=2,
        expiring_within_60_days=3,
        expiring_within_90_days=1,
        expiring_beyond_90_days=2,
        lease_turnover_exposure_pct=60.0,
        cliff_risk_level="HIGH",
    )
    fig = plot_lease_cliff_ladder(summary)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"

    # Missing rent roll handling
    fig_none = plot_lease_cliff_ladder(None)
    assert isinstance(fig_none, go.Figure)
    assert len(fig_none.layout.annotations) > 0


def test_dashboard_full_lifecycle_state_flow():
    """Verify dashboard end-to-end flow: run pipeline, pause at review, and submit approval."""
    demo_input = DEMO_PROPERTIES["Austin Downtown Luxury Condo (PROP-ATX-001)"]
    state = run_pipeline(demo_input)
    assert state["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"
    assert state["valuation"] is not None

    decision = HumanReviewEngine.approve_recommendation(
        reviewer_name="Dashboard User",
        reviewer_role="Analyst",
        valuation=state["valuation"],
        rental_pricing=state["rental_pricing"],
    )
    final_state = submit_human_decision(state, decision)
    assert final_state["workflow_status"] == "COMPLETED_APPROVED"
