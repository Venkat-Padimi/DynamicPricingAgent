"""Unit tests specifically verifying India-first real-estate localization features.

Validates Indian currency formatting (INR ₹, Lakh, Crore), Indian comma grouping,
BHK notation, RERA carpet area, PIN code handling, and Indian demonstration pipeline runs.
"""

import pytest

from src.core.enums import PropertyType, ReviewStatus
from src.core.formatters import (
    CURRENCY_CODE,
    CURRENCY_SYMBOL,
    format_bhk,
    format_inr,
    format_inr_short,
    format_psf,
    format_rent,
    indian_comma_format,
)
from src.core.intake_engine import PropertyIntakeEngine
from src.core.models import PropertyProfile
from src.reporting.reporter import generate_json_export, generate_markdown_dossier
from src.workflow.graph import run_pipeline


def test_indian_formatters_currency_constants():
    """Verify currency code and symbol constants conform to Indian INR standards."""
    assert CURRENCY_SYMBOL == "₹"
    assert CURRENCY_CODE == "INR"


def test_indian_comma_formatting():
    """Verify Indian numbering system comma grouping (1,00,000 and 1,00,00,000)."""
    assert indian_comma_format(0) == "0"
    assert indian_comma_format(500) == "500"
    assert indian_comma_format(1500) == "1,500"
    assert indian_comma_format(10000) == "10,000"
    assert indian_comma_format(65000) == "65,000"
    assert indian_comma_format(100000) == "1,00,000"  # 1 Lakh
    assert indian_comma_format(1250000) == "12,50,000"  # 12.5 Lakh
    assert indian_comma_format(10000000) == "1,00,00,000"  # 1 Crore
    assert indian_comma_format(16500000) == "1,65,00,000"  # 1.65 Crore


def test_format_inr_crore_and_lakh():
    """Verify format_inr with and without words for Lakh and Crore."""
    # Thousand
    assert "₹65,000" in format_inr(65000)
    # Lakh
    assert "₹85 Lakh" == format_inr(8500000, use_words=True)
    # Crore
    assert "₹1.65 Crore" == format_inr(16500000, use_words=True)
    # Without words
    assert "₹1,65,00,000" == format_inr(16500000, use_words=False)


def test_format_inr_short():
    """Verify concise display format for badges, charts, and metrics."""
    assert format_inr_short(16500000) == "₹1.65 Cr"
    assert format_inr_short(8500000) == "₹85.00 L"
    assert format_inr_short(65000) == "₹65.0 k"
    assert format_inr_short(0) == "₹0"


def test_format_rent_and_psf():
    """Verify monthly rental and per square foot rate formatters."""
    assert format_rent(65000) == "₹65,000/month"
    assert format_rent(65000, compact=True) == "₹65,000/mo"
    assert format_rent(8500.0, compact=True) == "₹8,500/mo"
    assert format_psf(7500) == "₹7,500/sq ft"
    assert format_psf(8918.92) == "₹8,919/sq ft"


def test_format_bhk():
    """Verify BHK (Bedroom-Hall-Kitchen) format notation."""
    assert format_bhk(1) == "1 BHK"
    assert format_bhk(2) == "2 BHK"
    assert format_bhk(3) == "3 BHK"
    assert format_bhk(4) == "4 BHK"
    assert format_bhk(0) == "Studio"


def test_indian_property_types_and_aliases():
    """Verify Indian property types and display names."""
    assert PropertyType.APARTMENT.display_name == "Apartment / Flat"
    assert PropertyType.INDEPENDENT_HOUSE.display_name == "Independent House / Villa"
    assert PropertyType.VILLA.display_name == "Villa / Row House"
    assert PropertyType.PLOT.display_name == "Residential Plot"
    assert PropertyType.COMMERCIAL.display_name == "Commercial"


def test_property_intake_indian_fields():
    """Verify property intake engine correctly ingests Indian fields: locality, carpet_area_sqft, pin_code."""
    raw = {
        "property_id": "PROP-HYD-001",
        "address": "Tower 4, My Home Bhooja, Silpa Gram, HITEC City",
        "city": "Hyderabad",
        "state": "Telangana",
        "pin_code": "500081",
        "locality": "HITEC City / Gachibowli",
        "property_type": "Apartment",
        "sqft": 1850.0,
        "carpet_area_sqft": 1450.0,
        "bedrooms": 3,
        "bathrooms": 3.0,
        "year_built": 2021,
        "condition": "Excellent",
        "amenities": ["Clubhouse", "Swimming Pool", "Gym", "Power Backup"],
        "parking_spaces": 2,
        "current_rent": 65000.0,
    }
    profile = PropertyIntakeEngine.parse_and_validate(raw)
    assert profile.property_id == "PROP-HYD-001"
    assert profile.city == "Hyderabad"
    assert profile.state == "Telangana"
    assert profile.zip_code == "500081"
    assert profile.pin_code == "500081"
    assert profile.locality == "HITEC City / Gachibowli"
    assert profile.carpet_area_sqft == 1450.0
    assert profile.bhk_display == "3 BHK"
    assert profile.property_type == PropertyType.APARTMENT


def test_pipeline_end_to_end_hyderabad_flagship():
    """Verify complete multi-agent pipeline execution on Hyderabad flagship property fixture."""
    hyderabad_input = {
        "property_id": "PROP-HYD-001",
        "address": "Tower 4, My Home Bhooja, Silpa Gram, HITEC City",
        "city": "Hyderabad",
        "state": "Telangana",
        "pin_code": "500081",
        "locality": "HITEC City",
        "property_type": "Apartment",
        "sqft": 1850.0,
        "carpet_area_sqft": 1450.0,
        "bedrooms": 3,
        "bathrooms": 3.0,
        "year_built": 2021,
        "condition": "Excellent",
        "amenities": ["Clubhouse", "Swimming Pool", "Gym", "Power Backup", "Covered Parking", "Balcony"],
        "parking_spaces": 2,
        "current_rent": 65000.0,
    }

    state = run_pipeline(hyderabad_input, initial_radius_miles=1.5)

    assert state["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"
    assert state["property_profile"].city == "Hyderabad"
    assert state["property_profile"].pin_code == "500081"

    # Valuation & Pricing checks
    val = state["valuation"]
    assert val.currency == "INR"
    assert val.currency_symbol == "₹"
    assert val.estimated_value > 10000000.0  # > ₹1 Crore realistic for HITEC City 3 BHK
    assert val.valuation_psf > 5000.0


    pricing = state["rental_pricing"]
    assert pricing.currency == "INR"
    assert pricing.recommended_midpoint > 40000.0  # > ₹40k/mo realistic for HITEC City 3 BHK

    # CMA checks
    cma = state["cma_analysis"]
    assert cma.currency == "INR"
    assert len(state["comparables"]) >= 3

    # Rent roll checks
    rent_roll = state["rent_roll_summary"]
    assert rent_roll.currency == "INR"
    assert rent_roll.total_units >= 5
    assert rent_roll.physical_occupancy_rate > 0.0

    # Risk & Quality
    risk = state["risk_report"]
    assert risk.overall_risk_severity is not None
    assert risk.data_quality_score > 0

    # Dossier formatting
    dossier = generate_markdown_dossier(state)
    assert "₹" in dossier
    assert "Hyderabad, Telangana" in dossier
    assert "500081" in dossier
    assert "Super Built-up Area" in dossier
    assert "3 BHK" in dossier
    assert "MANDATORY LEGAL & DECISION-SUPPORT DISCLAIMER" in dossier
    assert "NOT a legally binding appraisal" in dossier

    # JSON export
    import json
    json_data = json.loads(generate_json_export(state))
    assert json_data["report_metadata"]["currency"] == "INR"
    assert json_data["report_metadata"]["currency_symbol"] == "₹"
    assert json_data["report_metadata"]["locale"] == "en_IN"
