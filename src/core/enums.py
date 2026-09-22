"""Core enums for Automated Valuation & Dynamic Pricing Agent."""

from enum import Enum


class PropertyType(str, Enum):
    """Normalized residential and commercial property types."""
    SINGLE_FAMILY = "SingleFamily"
    CONDO = "Condo"
    TOWNHOUSE = "Townhouse"
    MULTI_FAMILY = "MultiFamily"
    COMMERCIAL = "Commercial"


class PropertyCondition(str, Enum):
    """Property physical condition rating."""
    POOR = "Poor"
    FAIR = "Fair"
    GOOD = "Good"
    EXCELLENT = "Excellent"
    LUXURY_RENOVATED = "LuxuryRenovated"


class DataOrigin(str, Enum):
    """Strict classification of data origin to prevent fabrication and enforce provenance."""
    VERIFIED_MARKET_DATA = "VERIFIED MARKET DATA"
    USER_PROVIDED_DATA = "USER-PROVIDED PROPERTY DATA"
    SYNTHETIC_DEMONSTRATION_DATA = "SYNTHETIC DEMONSTRATION DATA"
    MODEL_PREDICTIONS = "MODEL PREDICTIONS"
    AGENT_INTERPRETATIONS = "AGENT INTERPRETATIONS"


class ConfidenceLevel(str, Enum):
    """Deterministic confidence classifications."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReviewStatus(str, Enum):
    """Status of Human-in-the-Loop review."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"
    EVIDENCE_REQUESTED = "EVIDENCE_REQUESTED"


class RiskSeverity(str, Enum):
    """Severity levels for data quality and valuation risks."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LeaseStatus(str, Enum):
    """Operational status of a rental unit lease."""
    OCCUPIED = "OCCUPIED"
    VACANT = "VACANT"
    NOTICE_GIVEN = "NOTICE_GIVEN"
    RENEWAL_PENDING = "RENEWAL_PENDING"


class MarketTrendDirection(str, Enum):
    """Direction of market price and rental movement."""
    APPRECIATING = "APPRECIATING"
    STABLE = "STABLE"
    SOFTENING = "SOFTENING"
    DECLINING = "DECLINING"
