"""Core Pydantic models for the Automated Valuation & Dynamic Pricing Agent platform."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from src.core.enums import (
    ConfidenceLevel,
    DataOrigin,
    LeaseStatus,
    MarketTrendDirection,
    PropertyCondition,
    PropertyType,
    ReviewStatus,
    RiskSeverity,
)

LEGAL_DISCLAIMER_TEXT = (
    "Decision-Support Notice: This AI-assisted valuation is intended for research and decision-support "
    "purposes only. It is NOT a legally binding appraisal, registered valuation, or professional "
    "assessment under Indian law. Human review, verification against authoritative property records "
    "(Sub-Registrar / Municipal records), and appropriate professional assessment are required before "
    "financial, legal, lending, or investment decisions."
)

SYNTHETIC_NOTICE_TEXT = "Synthetic demonstration data — not real market data."


class ProvenanceMetadata(BaseModel):
    """Data provenance tracker guaranteeing source integrity."""
    source: str = Field(..., description="Originating provider, dataset name, or user input")
    origin: DataOrigin = Field(default=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    notice: str = Field(default=SYNTHETIC_NOTICE_TEXT)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    record_id: Optional[str] = Field(default=None, description="External or upstream identifier")

    @model_validator(mode="after")
    def enforce_synthetic_notice(self) -> "ProvenanceMetadata":
        if self.origin == DataOrigin.SYNTHETIC_DEMONSTRATION_DATA:
            if not self.notice:
                self.notice = SYNTHETIC_NOTICE_TEXT
        return self


class PropertyProfile(BaseModel):
    """Subject property specification parsed and normalized by Property Intake Agent."""
    property_id: str = Field(..., description="Unique subject property identifier")
    address: str
    city: str
    state: str
    zip_code: str = Field(..., description="PIN Code / Postal code")
    locality: Optional[str] = Field(default=None, description="Neighborhood / Locality / Sector")
    property_type: PropertyType = Field(default=PropertyType.APARTMENT)
    sqft: float = Field(..., gt=0, description="Gross built-up or super built-up area in square feet")
    carpet_area_sqft: Optional[float] = Field(default=None, ge=0, description="RERA carpet area in sq ft")
    bedrooms: int = Field(..., ge=0)
    bathrooms: float = Field(..., ge=0)
    year_built: int = Field(..., ge=1800, le=2030)
    lot_size_sqft: Optional[float] = Field(default=None, ge=0)
    condition: PropertyCondition = Field(default=PropertyCondition.GOOD)
    amenities: List[str] = Field(default_factory=list)
    parking_spaces: int = Field(default=1, ge=0)
    stories: int = Field(default=1, ge=1)
    hoa_monthly: float = Field(default=0.0, ge=0, description="Monthly maintenance / society charges in INR")
    current_rent: Optional[float] = Field(default=None, ge=0, description="Current in-place rent if leased in INR")
    occupancy_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    data_origin: DataOrigin = Field(default=DataOrigin.USER_PROVIDED_DATA)
    provenance: ProvenanceMetadata = Field(
        default_factory=lambda: ProvenanceMetadata(
            source="User Intake Form",
            origin=DataOrigin.USER_PROVIDED_DATA,
            notice="User-provided property specifications.",
        )
    )

    @property
    def pin_code(self) -> str:
        return self.zip_code

    @property
    def bhk_display(self) -> str:
        if self.bedrooms == 0:
            return "Studio / 1 RK"
        return f"{self.bedrooms} BHK"

    @property
    def age_years(self) -> int:
        return max(0, datetime.now(timezone.utc).year - self.year_built)


class MarketRecord(BaseModel):
    """Normalized comparable sales or rental market transaction record."""
    record_id: str
    address: str
    city: str
    state: str
    zip_code: str = Field(..., description="PIN Code / Postal code")
    locality: Optional[str] = Field(default=None, description="Neighborhood / Locality / Sector")
    property_type: PropertyType
    transaction_date: str = Field(..., description="ISO date YYYY-MM-DD")
    sale_price: Optional[float] = Field(default=None, ge=0, description="Sale price if closed sale in INR")
    monthly_rent: Optional[float] = Field(default=None, ge=0, description="Monthly rent if lease transaction in INR")
    sqft: float = Field(..., gt=0)
    carpet_area_sqft: Optional[float] = Field(default=None, ge=0)
    bedrooms: int = Field(..., ge=0)
    bathrooms: float = Field(..., ge=0)
    year_built: int
    condition: PropertyCondition = Field(default=PropertyCondition.GOOD)
    distance_miles: float = Field(default=0.5, ge=0.0, description="Distance from subject property in miles")
    days_on_market: Optional[int] = Field(default=None, ge=0)
    amenities: List[str] = Field(default_factory=list)
    parking_spaces: int = Field(default=1, ge=0)
    data_origin: DataOrigin = Field(default=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    provenance: ProvenanceMetadata

    @property
    def pin_code(self) -> str:
        return self.zip_code

    @property
    def distance_km(self) -> float:
        return round(self.distance_miles * 1.60934, 2)

    @property
    def bhk_display(self) -> str:
        if self.bedrooms == 0:
            return "Studio / 1 RK"
        return f"{self.bedrooms} BHK"

    @property
    def price_per_sqft(self) -> float:
        if self.sale_price and self.sale_price > 0:
            return round(self.sale_price / self.sqft, 2)
        return 0.0

    @property
    def rent_per_sqft(self) -> float:
        if self.monthly_rent and self.monthly_rent > 0:
            return round(self.monthly_rent / self.sqft, 2)
        return 0.0


class FeatureAdjustment(BaseModel):
    """Detailed line-item CMA feature adjustment."""
    feature_name: str
    subject_value: Any
    comp_value: Any
    raw_difference: float
    adjustment_rate: float = Field(..., description="Dollar impact per unit of difference")
    adjustment_amount: float = Field(..., description="Total dollar adjustment applied to comp price")
    rationale: str


class ComparableProperty(BaseModel):
    """CMA comparable property pairing subject property with comparable market record."""
    record: MarketRecord
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity index from 0.0 to 1.0")
    adjustments: List[FeatureAdjustment] = Field(default_factory=list)
    total_net_adjustment: float = Field(default=0.0)
    adjusted_price: float = Field(..., description="Comp sale price + total net adjustments")
    adjusted_price_psf: float = Field(..., description="Adjusted price divided by subject sqft")
    selection_rationale: str
    is_outlier: bool = Field(default=False)


class CMAAnalysis(BaseModel):
    """Comprehensive Comparative Market Analysis synthesis."""
    subject_property_id: str
    comparables: List[ComparableProperty] = Field(default_factory=list)
    unadjusted_median_price: float = Field(default=0.0)
    unadjusted_mean_price: float = Field(default=0.0)
    adjusted_median_price: float = Field(default=0.0)
    adjusted_mean_price: float = Field(default=0.0)
    adjusted_price_low: float = Field(default=0.0)
    adjusted_price_high: float = Field(default=0.0)
    adjusted_psf_mean: float = Field(default=0.0)
    outlier_count: int = Field(default=0)
    methodology_notes: str = Field(default="")
    currency: str = Field(default="INR")
    currency_symbol: str = Field(default="₹")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubmarketMetricPoint(BaseModel):
    """Historical monthly aggregate metric point for trend analysis."""
    period: str = Field(..., description="YYYY-MM")
    median_sale_price: float
    median_sale_psf: float
    median_monthly_rent: float
    median_rent_psf: float
    sales_volume: int
    avg_days_on_market: int
    inventory_months: float
    gross_rental_yield_pct: float


class MarketConditions(BaseModel):
    """Historical facts vs agent interpretation for submarket dynamics."""
    submarket_name: str
    time_horizon_months: int = Field(default=24)
    historical_points: List[SubmarketMetricPoint] = Field(default_factory=list)
    annual_price_growth_rate: float = Field(..., description="Annualized historical sales price trend percentage")
    annual_rent_growth_rate: float = Field(..., description="Annualized historical rental trend percentage")
    current_gross_yield_pct: float
    trend_direction: MarketTrendDirection
    factual_summary: str = Field(..., description="Strictly historical market facts")
    agent_interpretation: str = Field(..., description="Agent synthesis and forward projection")
    avg_inventory_months: Optional[float] = Field(default=None)
    avg_days_on_market: Optional[float] = Field(default=None)
    price_momentum_pct_6m: Optional[float] = Field(default=None)
    rent_momentum_pct_6m: Optional[float] = Field(default=None)
    data_origin: DataOrigin = Field(default=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    provenance: ProvenanceMetadata


class RentRollUnit(BaseModel):
    """Single unit in an operational rent roll. Eliminates tenant PII."""
    unit_id: str
    unit_number: str
    bedrooms: int
    bathrooms: float
    sqft: float
    current_rent: float
    in_place_psf: float
    lease_start: str = Field(..., description="YYYY-MM-DD")
    lease_end: str = Field(..., description="YYYY-MM-DD")
    days_until_expiration: int
    lease_status: LeaseStatus = Field(default=LeaseStatus.OCCUPIED)
    tenant_pseudonym: str = Field(
        ...,
        description="Anonymized hash or token (e.g. 'TENANT-89F1') - strictly NO real PII",
    )

    @property
    def bhk_display(self) -> str:
        if self.bedrooms == 0:
            return "Studio / 1 RK"
        return f"{self.bedrooms} BHK"


class RentRollSummary(BaseModel):
    """Operational summary of property leases and occupancy."""
    property_id: str
    total_units: int
    occupied_units: int
    physical_occupancy_rate: float
    economic_occupancy_rate: float = Field(default=0.0)
    physical_vacancy_rate: float = Field(default=0.0)
    economic_vacancy_rate: float = Field(default=0.0)
    gross_potential_monthly_rent: float
    current_in_place_monthly_rent: float
    gross_annual_in_place_rent: float = Field(default=0.0)
    avg_rent_per_unit: float
    avg_rent_psf: float
    expiring_within_30_days: int
    expiring_within_60_days: int
    expiring_within_90_days: int
    expiring_beyond_90_days: int
    expiring_rent_within_90_days: float = Field(default=0.0)
    expiring_sqft_within_90_days: float = Field(default=0.0)
    lease_turnover_exposure_pct: float
    cliff_risk_level: str = Field(default="LOW")
    potential_rent_gap: float = Field(default=0.0, description="Gross potential rent minus in-place rent")
    currency: str = Field(default="INR")
    currency_symbol: str = Field(default="₹")
    data_origin: DataOrigin = Field(default=DataOrigin.SYNTHETIC_DEMONSTRATION_DATA)
    provenance: Optional[ProvenanceMetadata] = Field(default=None)


class ValuationComponentBreakdown(BaseModel):
    """Transparent deterministic valuation calculation breakdown."""
    cma_sales_component: float = Field(..., description="Weighted adjusted sales comparable estimate")
    cma_weight: float = Field(default=0.60)
    property_feature_adjustment: float = Field(default=0.0, description="Net amenity and condition premium")
    market_trend_component: float = Field(default=0.0, description="Adjustment based on submarket momentum")
    market_trend_weight: float = Field(default=0.15)
    location_component: float = Field(default=0.0, description="Micro-location neighborhood factor")
    location_weight: float = Field(default=0.10)
    income_capitalization_component: Optional[float] = Field(
        default=None, description="Yield/cap-rate capitalized value if rental data present"
    )
    income_weight: float = Field(default=0.15)
    data_quality_adjustment: float = Field(default=0.0, description="Haircut penalty for stale or sparse data")


class ValuationResult(BaseModel):
    """Estimated market valuation recommendation produced by Valuation Agent."""
    property_id: str
    estimated_value: float = Field(..., gt=0)
    valuation_range_low: float = Field(..., gt=0)
    valuation_range_high: float = Field(..., gt=0)
    valuation_psf: float = Field(..., gt=0)
    currency: str = Field(default="INR")
    currency_symbol: str = Field(default="₹")
    confidence_level: ConfidenceLevel
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    breakdown: ValuationComponentBreakdown
    key_drivers: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    methodology: str
    legal_disclaimer: str = Field(default=LEGAL_DISCLAIMER_TEXT)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RentalPricingBreakdown(BaseModel):
    """Deterministic rental pricing breakdown components."""
    base_market_comp_rent: float
    occupancy_leverage_adjustment: float = Field(default=0.0)
    lease_expiration_timing_adjustment: float = Field(default=0.0)
    property_condition_premium: float = Field(default=0.0)
    submarket_momentum_adjustment: float = Field(default=0.0)


class RentalPricingResult(BaseModel):
    """Recommended monthly rental pricing range produced by Dynamic Pricing Agent."""
    property_id: str
    current_in_place_rent: Optional[float] = None
    estimated_market_rent: float = Field(..., gt=0)
    recommended_rent_range_low: float = Field(..., gt=0)
    recommended_rent_range_high: float = Field(..., gt=0)
    recommended_midpoint: float = Field(..., gt=0)
    rent_gap_amount: Optional[float] = None
    rent_gap_percentage: Optional[float] = None
    currency: str = Field(default="INR")
    currency_symbol: str = Field(default="₹")
    confidence_level: ConfidenceLevel
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    breakdown: RentalPricingBreakdown
    pricing_drivers: List[str] = Field(default_factory=list)
    seasonal_factors: str = Field(default="Standard seasonal baseline")
    disclaimer: str = Field(default=LEGAL_DISCLAIMER_TEXT)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RiskItem(BaseModel):
    """Individual risk or data quality warning."""
    risk_id: str
    severity: RiskSeverity
    category: str = Field(..., description="e.g. COMP_DATA, FRESHNESS, OUTLIER, RENT_ROLL, VARIANCE")
    message: str
    affected_fields: List[str] = Field(default_factory=list)
    recommendation: str


class RiskReport(BaseModel):
    """Comprehensive risk and data quality assessment."""
    overall_risk_severity: RiskSeverity
    data_quality_score: float = Field(..., ge=0.0, le=100.0)
    is_stale_data: bool = Field(default=False)
    is_insufficient_comps: bool = Field(default=False)
    is_missing_rentroll: bool = Field(default=False)
    is_conflicting_data: bool = Field(default=False)
    high_variance_warning: bool = Field(default=False)
    items: List[RiskItem] = Field(default_factory=list)
    summary: str


class HumanReviewDecision(BaseModel):
    """Enforced Human-in-the-Loop decision record."""
    review_id: str
    reviewer_name: str
    reviewer_role: str = Field(default="Real Estate Asset Manager")
    status: ReviewStatus = Field(default=ReviewStatus.PENDING)
    original_valuation: float
    original_recommended_rent: float
    modified_valuation: Optional[float] = None
    modified_recommended_rent: Optional[float] = None
    currency: str = Field(default="INR")
    currency_symbol: str = Field(default="₹")
    reviewer_notes: str = Field(default="")
    evidence_request_details: Optional[str] = None
    decision_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEntry(BaseModel):
    """Structured audit trail item recording each agent execution."""
    step_index: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_name: str
    action: str
    inputs_summary: str
    outputs_summary: str
    sources_consulted: List[str] = Field(default_factory=list)
    execution_time_ms: float
    warnings_issued: List[str] = Field(default_factory=list)
    decision: Optional[str] = None
