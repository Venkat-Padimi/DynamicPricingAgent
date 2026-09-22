"""Data provider abstract base classes."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.enums import PropertyType
from src.core.models import (
    MarketConditions,
    MarketRecord,
    RentRollSummary,
    RentRollUnit,
)


class BaseMarketDataProvider(ABC):
    """Abstract interface for market transaction data providers.

    Future implementations can plug in MLS (RESO Web API), ATTOM Data,
    CoStar, Redfin, Zillow, or local county recorder databases.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identification."""
        pass

    @abstractmethod
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
        """Retrieve closed sales transactions matching criteria."""
        pass

    @abstractmethod
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
        """Retrieve recent rental transactions matching criteria."""
        pass

    @abstractmethod
    def get_market_trends(
        self,
        submarket_name: str,
        time_horizon_months: int = 24,
    ) -> Optional[MarketConditions]:
        """Retrieve historical market trend data for submarket."""
        pass


class BaseRentRollProvider(ABC):
    """Abstract interface for property management and operational rent-roll providers.

    Future implementations can plug in RealPage, Yardi Voyager, AppFolio,
    Entrata, or CSV rent-roll imports.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identification."""
        pass

    @abstractmethod
    def get_rent_roll(self, property_id: str) -> List[RentRollUnit]:
        """Retrieve unit-level rent roll for a given property ID."""
        pass

    @abstractmethod
    def get_rent_roll_summary(self, property_id: str) -> Optional[RentRollSummary]:
        """Calculate and return operational rent roll summary for property."""
        pass
