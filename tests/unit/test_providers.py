"""Unit tests for Market Data and Rent-Roll Providers."""

import pytest
from src.core.enums import DataOrigin, LeaseStatus, PropertyType
from src.core.models import SYNTHETIC_NOTICE_TEXT
from src.data.providers.synthetic_provider import (
    SyntheticMarketDataProvider,
    SyntheticRentRollProvider,
)


@pytest.fixture
def market_provider():
    return SyntheticMarketDataProvider()


@pytest.fixture
def rentroll_provider():
    return SyntheticRentRollProvider()


def test_provider_provenance_integrity(market_provider):
    """Verify that all records returned by synthetic provider have explicit synthetic provenance."""
    comps = market_provider.get_sales_comps(city="Austin", zip_code="78701", limit=10)
    assert len(comps) > 0
    for comp in comps:
        assert comp.data_origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA
        assert comp.provenance.origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA
        assert comp.provenance.notice == SYNTHETIC_NOTICE_TEXT
        assert "Synthetic" in comp.provenance.source


def test_sales_comps_filtering_by_distance_and_sqft(market_provider):
    """Verify distance and sqft range filters on sales comps."""
    # Strict 0.3 miles radius
    close_comps = market_provider.get_sales_comps(
        city="Austin", zip_code="78701", max_distance_miles=0.3
    )
    for c in close_comps:
        assert c.distance_miles <= 0.3

    # Sqft filtering: 1100 to 1200 sqft
    sqft_comps = market_provider.get_sales_comps(
        city="Austin", zip_code="78701", min_sqft=1100.0, max_sqft=1200.0
    )
    for c in sqft_comps:
        assert 1100.0 <= c.sqft <= 1200.0


def test_rental_comps_query(market_provider):
    """Verify rental comps retrieval and rental metric calculations."""
    rentals = market_provider.get_rental_comps(city="Austin", zip_code="78701", limit=5)
    assert len(rentals) > 0
    for r in rentals:
        assert r.monthly_rent is not None
        assert r.monthly_rent > 0
        assert r.rent_per_sqft > 0
        assert r.data_origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA


def test_market_trends_retrieval(market_provider):
    """Verify 24-month historical trend retrieval and factual vs interpretation distinction."""
    trends = market_provider.get_market_trends("Austin-Downtown", time_horizon_months=24)
    assert trends is not None
    assert trends.submarket_name == "Austin-Downtown"
    assert len(trends.historical_points) == 24
    assert trends.annual_price_growth_rate > 0
    assert trends.annual_rent_growth_rate > 0
    assert trends.current_gross_yield_pct > 0
    assert "factual_summary" in trends.model_dump()
    assert "agent_interpretation" in trends.model_dump()
    assert trends.provenance.notice == SYNTHETIC_NOTICE_TEXT

    # Missing submarket returns None
    missing = market_provider.get_market_trends("NonExistentSubmarket999")
    assert missing is None


def test_rent_roll_units_and_anonymization(rentroll_provider):
    """Verify rent roll unit retrieval, pseudonymization, and zero PII."""
    units = rentroll_provider.get_rent_roll("PROP-ATX-001")
    assert len(units) == 8
    for u in units:
        assert u.tenant_pseudonym.startswith("TENANT-")
        assert "@" not in u.tenant_pseudonym  # No emails
        assert " " not in u.tenant_pseudonym  # No names
        assert u.sqft > 0
        if u.lease_status == LeaseStatus.OCCUPIED:
            assert u.current_rent > 0
            assert u.in_place_psf > 0


def test_rent_roll_summary_calculations(rentroll_provider):
    """Verify operational rent roll calculations including occupancy, gap, and expirations."""
    summary = rentroll_provider.get_rent_roll_summary("PROP-ATX-001")
    assert summary is not None
    assert summary.total_units == 8
    # In PROP-ATX-001 fixture: 1 unit is VACANT, 1 is NOTICE_GIVEN, 1 is RENEWAL_PENDING, 5 are OCCUPIED
    assert summary.occupied_units == 5
    assert summary.physical_occupancy_rate == round(5 / 8, 4)
    assert summary.gross_potential_monthly_rent > summary.current_in_place_monthly_rent
    assert summary.potential_rent_gap > 0
    assert summary.expiring_within_30_days >= 0
    assert summary.expiring_within_60_days >= 0
    assert summary.expiring_within_90_days >= 0
    assert summary.lease_turnover_exposure_pct >= 0


def test_rent_roll_missing_property(rentroll_provider):
    """Verify graceful handling for non-existent property."""
    units = rentroll_provider.get_rent_roll("PROP-NON-EXISTENT")
    assert units == []
    summary = rentroll_provider.get_rent_roll_summary("PROP-NON-EXISTENT")
    assert summary is None
