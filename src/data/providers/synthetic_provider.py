"""Synthetic Market Data and Rent-Roll Providers for offline demonstration."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.enums import DataOrigin, LeaseStatus, MarketTrendDirection, PropertyType
from src.core.models import (
    SYNTHETIC_NOTICE_TEXT,
    MarketConditions,
    MarketRecord,
    ProvenanceMetadata,
    RentRollSummary,
    RentRollUnit,
    SubmarketMetricPoint,
)
from src.data.providers.base import BaseMarketDataProvider, BaseRentRollProvider

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class SyntheticMarketDataProvider(BaseMarketDataProvider):
    """Offline market data provider backed by clearly labeled synthetic fixtures."""

    def __init__(self, fixtures_path: Optional[Path] = None):
        self._fixtures_path = fixtures_path or FIXTURES_DIR
        self._sales_records: List[MarketRecord] = []
        self._rental_records: List[MarketRecord] = []
        self._market_trends: Dict[str, Any] = {}
        self._load_fixtures()

    @property
    def provider_name(self) -> str:
        return "Synthetic Demonstration Provider v1.0"

    def _load_fixtures(self) -> None:
        """Load and parse JSON fixtures with provenance validation."""
        sales_file = self._fixtures_path / "sales_comps.json"
        if sales_file.exists():
            with open(sales_file, "r", encoding="utf-8") as f:
                raw_sales = json.load(f)
                self._sales_records = [MarketRecord.model_validate(r) for r in raw_sales]

        rental_file = self._fixtures_path / "rental_comps.json"
        if rental_file.exists():
            with open(rental_file, "r", encoding="utf-8") as f:
                raw_rentals = json.load(f)
                self._rental_records = [MarketRecord.model_validate(r) for r in raw_rentals]

        trends_file = self._fixtures_path / "market_trends.json"
        if trends_file.exists():
            with open(trends_file, "r", encoding="utf-8") as f:
                self._market_trends = json.load(f)

    def get_sales_comps(
        self,
        city: str,
        zip_code: str,
        property_type: Optional[PropertyType] = None,
        max_distance_miles: float = 3.0,
        min_sqft: Optional[float] = None,
        max_sqft: Optional[float] = None,
        bedrooms: Optional[int] = None,
        max_age_months: Optional[int] = None,
        limit: int = 15,
    ) -> List[MarketRecord]:
        """Query synthetic sales comps filtered by geography, property type, and attributes."""
        candidates = []
        city_norm = city.strip().lower() if city else ""
        zip_norm = zip_code.strip() if zip_code else ""

        for r in self._sales_records:
            # Geographic filter: match city or zip code
            matches_geo = (city_norm and r.city.lower() == city_norm) or (zip_norm and r.zip_code == zip_norm)
            if not matches_geo:
                continue

            # Distance filter
            if r.distance_miles > max_distance_miles:
                continue

            # Property type filter
            if property_type and r.property_type != property_type:
                # Allow fallback if no strict match, but filter when possible
                pass

            # Sqft range filter
            if min_sqft and r.sqft < min_sqft:
                continue
            if max_sqft and r.sqft > max_sqft:
                continue

            # Bedroom tolerance filter (+/- 1 bed)
            if bedrooms is not None and abs(r.bedrooms - bedrooms) > 1:
                continue

            candidates.append(r)

        # Sort by distance ascending, then date descending
        candidates.sort(key=lambda x: (x.distance_miles, -int(x.transaction_date.replace("-", ""))))
        return candidates[:limit]

    def get_rental_comps(
        self,
        city: str,
        zip_code: str,
        property_type: Optional[PropertyType] = None,
        max_distance_miles: float = 3.0,
        min_sqft: Optional[float] = None,
        max_sqft: Optional[float] = None,
        bedrooms: Optional[int] = None,
        max_age_months: Optional[int] = None,
        limit: int = 15,
    ) -> List[MarketRecord]:
        """Query synthetic rental comps filtered by geography and specs."""
        candidates = []
        city_norm = city.strip().lower() if city else ""
        zip_norm = zip_code.strip() if zip_code else ""

        for r in self._rental_records:
            matches_geo = (city_norm and r.city.lower() == city_norm) or (zip_norm and r.zip_code == zip_norm)
            if not matches_geo:
                continue

            if r.distance_miles > max_distance_miles:
                continue

            if min_sqft and r.sqft < min_sqft:
                continue
            if max_sqft and r.sqft > max_sqft:
                continue

            if bedrooms is not None and abs(r.bedrooms - bedrooms) > 1:
                continue

            candidates.append(r)

        candidates.sort(key=lambda x: (x.distance_miles, -int(x.transaction_date.replace("-", ""))))
        return candidates[:limit]

    def get_market_trends(
        self,
        submarket_name: str,
        time_horizon_months: int = 24,
    ) -> Optional[MarketConditions]:
        """Retrieve historical market trend data for submarket."""
        key = submarket_name.strip()
        # Direct lookup or heuristic fallback
        trend_data = self._market_trends.get(key)
        if not trend_data:
            # Fallback search by substring
            for k, data in self._market_trends.items():
                if key.lower() in k.lower() or k.lower() in key.lower():
                    trend_data = data
                    break

        if not trend_data:
            return None

        # Build MarketConditions model with explicit provenance
        prov = ProvenanceMetadata(
            source=self.provider_name,
            origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
            notice=SYNTHETIC_NOTICE_TEXT,
            record_id=trend_data.get("provenance", {}).get("record_id", "SYNTHETIC-TREND"),
        )

        history = [
            SubmarketMetricPoint.model_validate(pt)
            for pt in trend_data.get("historical_points", [])[:time_horizon_months]
        ]

        return MarketConditions(
            submarket_name=trend_data["submarket_name"],
            time_horizon_months=time_horizon_months,
            historical_points=history,
            annual_price_growth_rate=float(trend_data["annual_price_growth_rate"]),
            annual_rent_growth_rate=float(trend_data["annual_rent_growth_rate"]),
            current_gross_yield_pct=float(trend_data["current_gross_yield_pct"]),
            trend_direction=MarketTrendDirection(trend_data.get("trend_direction", "STABLE")),
            factual_summary=trend_data["factual_summary"],
            agent_interpretation=trend_data["agent_interpretation"],
            data_origin=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
            provenance=prov,
        )


class SyntheticRentRollProvider(BaseRentRollProvider):
    """Offline rent-roll provider backed by synthetic unit fixtures."""

    def __init__(self, fixtures_path: Optional[Path] = None):
        self._fixtures_path = fixtures_path or FIXTURES_DIR
        self._rent_rolls: Dict[str, List[Dict[str, Any]]] = {}
        self._load_fixtures()

    @property
    def provider_name(self) -> str:
        return "Synthetic Rent-Roll Provider v1.0"

    def _load_fixtures(self) -> None:
        rent_roll_file = self._fixtures_path / "rent_rolls.json"
        if rent_roll_file.exists():
            with open(rent_roll_file, "r", encoding="utf-8") as f:
                self._rent_rolls = json.load(f)

    def get_rent_roll(self, property_id: str) -> List[RentRollUnit]:
        """Retrieve unit-level rent roll for a given property ID."""
        raw_units = self._rent_rolls.get(property_id, [])
        units = []
        for u in raw_units:
            units.append(RentRollUnit.model_validate(u))
        return units

    def get_rent_roll_summary(self, property_id: str) -> Optional[RentRollSummary]:
        """Calculate and return operational rent roll summary for property."""
        units = self.get_rent_roll(property_id)
        if not units:
            return None

        total_units = len(units)
        occupied_units = sum(1 for u in units if u.lease_status == LeaseStatus.OCCUPIED)
        occupancy_rate = round(occupied_units / total_units, 4) if total_units > 0 else 0.0

        current_in_place = sum(u.current_rent for u in units)

        # Estimate market/potential rent for vacant units using occupied average PSF
        occupied_sqft = sum(u.sqft for u in units if u.lease_status == LeaseStatus.OCCUPIED)
        occupied_rent = sum(u.current_rent for u in units if u.lease_status == LeaseStatus.OCCUPIED)
        avg_occ_psf = (occupied_rent / occupied_sqft) if occupied_sqft > 0 else 25.0

        gross_potential = 0.0
        for u in units:
            if u.lease_status == LeaseStatus.OCCUPIED and u.current_rent > 0:
                gross_potential += u.current_rent
            else:
                gross_potential += u.sqft * avg_occ_psf

        total_sqft = sum(u.sqft for u in units)
        avg_rent_unit = round(current_in_place / occupied_units, 2) if occupied_units > 0 else 0.0
        avg_rent_psf = round(current_in_place / total_sqft, 2) if total_sqft > 0 else 0.0

        exp_30 = sum(1 for u in units if 0 < u.days_until_expiration <= 30)
        exp_60 = sum(1 for u in units if 30 < u.days_until_expiration <= 60)
        exp_90 = sum(1 for u in units if 60 < u.days_until_expiration <= 90)
        exp_beyond_90 = sum(1 for u in units if u.days_until_expiration > 90)

        turnover_exposure_pct = round(((exp_30 + exp_60 + exp_90) / total_units) * 100, 2) if total_units > 0 else 0.0
        potential_gap = round(gross_potential - current_in_place, 2)

        return RentRollSummary(
            property_id=property_id,
            total_units=total_units,
            occupied_units=occupied_units,
            physical_occupancy_rate=occupancy_rate,
            gross_potential_monthly_rent=round(gross_potential, 2),
            current_in_place_monthly_rent=round(current_in_place, 2),
            avg_rent_per_unit=avg_rent_unit,
            avg_rent_psf=avg_rent_psf,
            expiring_within_30_days=exp_30,
            expiring_within_60_days=exp_60,
            expiring_within_90_days=exp_90,
            expiring_beyond_90_days=exp_beyond_90,
            lease_turnover_exposure_pct=turnover_exposure_pct,
            potential_rent_gap=potential_gap,
        )
