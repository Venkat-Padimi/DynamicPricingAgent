"""Unit tests for Lease Analysis Engine, Market Conditions Engine, and Privacy Safeguards."""

import pytest
from src.core.enums import DataOrigin, LeaseStatus, MarketTrendDirection
from src.core.lease_engine import LeaseAnalysisEngine
from src.core.market_conditions_engine import MarketConditionsEngine
from src.core.models import (
    SYNTHETIC_NOTICE_TEXT,
    ProvenanceMetadata,
    RentRollUnit,
    SubmarketMetricPoint,
)
from src.data.providers.synthetic_provider import (
    SyntheticMarketDataProvider,
    SyntheticRentRollProvider,
)


@pytest.fixture
def rentroll_provider():
    return SyntheticRentRollProvider()


@pytest.fixture
def market_provider():
    return SyntheticMarketDataProvider()


def test_lease_analysis_engine_metrics(rentroll_provider):
    """Verify deterministic physical/economic occupancy, vacancy, and rent gap calculations."""
    units = rentroll_provider.get_rent_roll("PROP-ATX-001")
    summary = LeaseAnalysisEngine.analyze_rent_roll("PROP-ATX-001", units)

    assert summary is not None
    assert summary.total_units == 8
    assert summary.occupied_units == 5
    assert summary.physical_occupancy_rate == 0.625
    assert summary.physical_vacancy_rate == 0.375

    # In-place monthly rent must be positive and match occupied units sum
    assert summary.current_in_place_monthly_rent > 0
    assert summary.gross_annual_in_place_rent == round(summary.current_in_place_monthly_rent * 12.0, 2)

    # Gross potential must be >= in-place rent
    assert summary.gross_potential_monthly_rent >= summary.current_in_place_monthly_rent
    assert summary.potential_rent_gap >= 0
    assert summary.economic_occupancy_rate <= 1.0
    assert summary.economic_vacancy_rate >= 0.0
    assert round(summary.economic_occupancy_rate + summary.economic_vacancy_rate, 4) == 1.0


def test_lease_expiration_cliff_analysis():
    """Verify 30/60/90 day lease expiration cliff ladder and risk level assignment."""
    units = [
        RentRollUnit(
            unit_id="U1", unit_number="1", bedrooms=1, bathrooms=1.0, sqft=700.0,
            current_rent=2000.0, in_place_psf=2.86, lease_start="2025-01-01", lease_end="2025-11-01",
            days_until_expiration=20, lease_status=LeaseStatus.OCCUPIED, tenant_pseudonym="TENANT-U1",
        ),
        RentRollUnit(
            unit_id="U2", unit_number="2", bedrooms=1, bathrooms=1.0, sqft=700.0,
            current_rent=2100.0, in_place_psf=3.00, lease_start="2025-01-01", lease_end="2025-11-20",
            days_until_expiration=50, lease_status=LeaseStatus.OCCUPIED, tenant_pseudonym="TENANT-U2",
        ),
        RentRollUnit(
            unit_id="U3", unit_number="3", bedrooms=2, bathrooms=2.0, sqft=1000.0,
            current_rent=3000.0, in_place_psf=3.00, lease_start="2025-01-01", lease_end="2025-12-15",
            days_until_expiration=80, lease_status=LeaseStatus.OCCUPIED, tenant_pseudonym="TENANT-U3",
        ),
        RentRollUnit(
            unit_id="U4", unit_number="4", bedrooms=2, bathrooms=2.0, sqft=1000.0,
            current_rent=3100.0, in_place_psf=3.10, lease_start="2025-01-01", lease_end="2026-06-30",
            days_until_expiration=240, lease_status=LeaseStatus.OCCUPIED, tenant_pseudonym="TENANT-U4",
        ),
    ]

    summary = LeaseAnalysisEngine.analyze_rent_roll("TEST-CLIFF", units)
    assert summary is not None
    assert summary.expiring_within_30_days == 1
    assert summary.expiring_within_60_days == 1
    assert summary.expiring_within_90_days == 1
    assert summary.expiring_beyond_90_days == 1
    # 3 of 4 units expiring in <= 90 days = 75% -> HIGH cliff risk
    assert summary.lease_turnover_exposure_pct == 75.0
    assert summary.cliff_risk_level == "HIGH"
    assert summary.expiring_rent_within_90_days == 2000.0 + 2100.0 + 3000.0


def test_tenant_pii_strict_protection():
    """Verify strict elimination of personal names, emails, and phone numbers from rent roll."""
    # Valid pseudonyms
    valid_units = [
        RentRollUnit(
            unit_id="U1", unit_number="1", bedrooms=1, bathrooms=1.0, sqft=700.0,
            current_rent=2000.0, in_place_psf=2.86, lease_start="2025-01-01", lease_end="2026-01-01",
            days_until_expiration=120, lease_status=LeaseStatus.OCCUPIED, tenant_pseudonym="TENANT-7F9A",
        )
    ]
    assert LeaseAnalysisEngine.verify_tenant_privacy(valid_units) is True

    # PII violation: email in pseudonym
    invalid_email = [
        RentRollUnit(
            unit_id="U1", unit_number="1", bedrooms=1, bathrooms=1.0, sqft=700.0,
            current_rent=2000.0, in_place_psf=2.86, lease_start="2025-01-01", lease_end="2026-01-01",
            days_until_expiration=120, lease_status=LeaseStatus.OCCUPIED, tenant_pseudonym="TENANT-john@gmail.com",
        )
    ]
    assert LeaseAnalysisEngine.verify_tenant_privacy(invalid_email) is False

    # PII violation: full name with spaces
    invalid_name = [
        RentRollUnit(
            unit_id="U1", unit_number="1", bedrooms=1, bathrooms=1.0, sqft=700.0,
            current_rent=2000.0, in_place_psf=2.86, lease_start="2025-01-01", lease_end="2026-01-01",
            days_until_expiration=120, lease_status=LeaseStatus.OCCUPIED, tenant_pseudonym="TENANT-John Doe",
        )
    ]
    assert LeaseAnalysisEngine.verify_tenant_privacy(invalid_name) is False


def test_lease_fact_vs_interpretation_separation(rentroll_provider):
    """Verify separation of factual operational statements from interpretive recommendations."""
    units = rentroll_provider.get_rent_roll("PROP-ATX-001")
    summary = LeaseAnalysisEngine.analyze_rent_roll("PROP-ATX-001", units)
    facts, interp = LeaseAnalysisEngine.generate_narratives(summary)

    assert "Property operates at" in facts
    assert "% physical occupancy" in facts
    assert ("Elevated lease cliff risk" in interp or "Moderate lease rollover" in interp or "Stable lease" in interp)
    assert summary.provenance is None or summary.provenance.origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA


def test_market_conditions_cagr_and_momentum():
    """Verify deterministic annualized growth and trailing momentum calculations."""
    points = [
        SubmarketMetricPoint(period="2024-01", median_sale_price=500000.0, median_sale_psf=400.0, median_monthly_rent=2000.0, median_rent_psf=2.00, sales_volume=20, avg_days_on_market=30, inventory_months=2.5, gross_rental_yield_pct=6.00),
        SubmarketMetricPoint(period="2024-07", median_sale_price=510000.0, median_sale_psf=410.0, median_monthly_rent=2050.0, median_rent_psf=2.05, sales_volume=22, avg_days_on_market=28, inventory_months=2.4, gross_rental_yield_pct=6.00),
        SubmarketMetricPoint(period="2025-01", median_sale_price=530000.0, median_sale_psf=425.0, median_monthly_rent=2150.0, median_rent_psf=2.15, sales_volume=25, avg_days_on_market=26, inventory_months=2.2, gross_rental_yield_pct=6.07),
    ]

    cond = MarketConditionsEngine.calculate_metrics_from_points("Austin-Central", points, time_horizon_months=24)
    assert cond is not None
    assert cond.annual_price_growth_rate > 0
    assert cond.annual_rent_growth_rate > 0
    assert cond.trend_direction == MarketTrendDirection.APPRECIATING
    assert cond.current_gross_yield_pct == 6.07
    assert cond.data_origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA
    assert cond.provenance.notice == SYNTHETIC_NOTICE_TEXT
    assert "Historical facts" in cond.factual_summary
    assert len(cond.agent_interpretation) > 0


def test_market_conditions_edge_cases():
    """Verify graceful handling for empty, single-point, or softening market data."""
    # Empty points
    assert MarketConditionsEngine.calculate_metrics_from_points("Submarket", []) is None

    # Single point
    pt_single = [SubmarketMetricPoint(period="2025-01", median_sale_price=500000.0, median_sale_psf=400.0, median_monthly_rent=2000.0, median_rent_psf=2.00, sales_volume=20, avg_days_on_market=30, inventory_months=2.5, gross_rental_yield_pct=6.00)]
    cond_single = MarketConditionsEngine.calculate_metrics_from_points("Submarket", pt_single)
    assert cond_single is not None
    assert cond_single.annual_price_growth_rate == 0.0
    assert cond_single.trend_direction == MarketTrendDirection.STABLE

    # Softening market
    softening_points = [
        SubmarketMetricPoint(period="2024-01", median_sale_price=500000.0, median_sale_psf=500.0, median_monthly_rent=2500.0, median_rent_psf=2.50, sales_volume=20, avg_days_on_market=30, inventory_months=2.5, gross_rental_yield_pct=6.00),
        SubmarketMetricPoint(period="2025-01", median_sale_price=480000.0, median_sale_psf=480.0, median_monthly_rent=2400.0, median_rent_psf=2.40, sales_volume=15, avg_days_on_market=45, inventory_months=3.8, gross_rental_yield_pct=6.00),
    ]
    cond_soft = MarketConditionsEngine.calculate_metrics_from_points("SoftMarket", softening_points)
    assert cond_soft is not None
    assert cond_soft.annual_price_growth_rate < 0
    assert cond_soft.trend_direction in [MarketTrendDirection.SOFTENING, MarketTrendDirection.DECLINING]


def test_deterministic_reproducibility():
    """Verify that repeated calculations yield identical results down to the penny."""
    pts = [
        SubmarketMetricPoint(period="2024-01", median_sale_price=500000.0, median_sale_psf=400.0, median_monthly_rent=2000.0, median_rent_psf=2.00, sales_volume=20, avg_days_on_market=30, inventory_months=2.5, gross_rental_yield_pct=6.00),
        SubmarketMetricPoint(period="2025-01", median_sale_price=520000.0, median_sale_psf=416.0, median_monthly_rent=2080.0, median_rent_psf=2.08, sales_volume=22, avg_days_on_market=27, inventory_months=2.3, gross_rental_yield_pct=6.00),
    ]
    cond1 = MarketConditionsEngine.calculate_metrics_from_points("Submarket", pts)
    cond2 = MarketConditionsEngine.calculate_metrics_from_points("Submarket", pts)
    assert cond1.annual_price_growth_rate == cond2.annual_price_growth_rate
    assert cond1.current_gross_yield_pct == cond2.current_gross_yield_pct
    assert cond1.factual_summary == cond2.factual_summary
