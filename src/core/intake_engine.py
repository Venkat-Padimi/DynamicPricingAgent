"""Property Intake Engine for parsing, normalizing, and validating subject property inputs."""

import uuid
from typing import Any, Dict, List, Optional

from src.core.enums import DataOrigin, PropertyCondition, PropertyType
from src.core.models import PropertyProfile, ProvenanceMetadata


class PropertyIntakeEngine:
    """Parses and normalizes raw user or API property inputs into validated PropertyProfile."""

    PROPERTY_TYPE_MAP = {
        "single_family": PropertyType.SINGLE_FAMILY,
        "singlefamily": PropertyType.SINGLE_FAMILY,
        "house": PropertyType.SINGLE_FAMILY,
        "condo": PropertyType.CONDO,
        "condominium": PropertyType.CONDO,
        "townhouse": PropertyType.TOWNHOUSE,
        "townhome": PropertyType.TOWNHOUSE,
        "multifamily": PropertyType.MULTI_FAMILY,
        "multi_family": PropertyType.MULTI_FAMILY,
        "apartment": PropertyType.MULTI_FAMILY,
        "commercial": PropertyType.COMMERCIAL,
    }

    CONDITION_MAP = {
        "poor": PropertyCondition.POOR,
        "fair": PropertyCondition.FAIR,
        "good": PropertyCondition.GOOD,
        "average": PropertyCondition.GOOD,
        "excellent": PropertyCondition.EXCELLENT,
        "luxury": PropertyCondition.LUXURY_RENOVATED,
        "luxuryrenovated": PropertyCondition.LUXURY_RENOVATED,
        "renovated": PropertyCondition.LUXURY_RENOVATED,
    }

    @classmethod
    def normalize_property_type(cls, raw_type: Any) -> PropertyType:
        """Normalize freeform string into standard PropertyType enum."""
        if isinstance(raw_type, PropertyType):
            return raw_type
        if not raw_type:
            return PropertyType.SINGLE_FAMILY
        cleaned = str(raw_type).strip().lower().replace("-", "_").replace(" ", "_")
        return cls.PROPERTY_TYPE_MAP.get(cleaned, PropertyType.SINGLE_FAMILY)

    @classmethod
    def normalize_condition(cls, raw_condition: Any) -> PropertyCondition:
        """Normalize freeform string into standard PropertyCondition enum."""
        if isinstance(raw_condition, PropertyCondition):
            return raw_condition
        if not raw_condition:
            return PropertyCondition.GOOD
        cleaned = str(raw_condition).strip().lower().replace("-", "").replace(" ", "")
        return cls.CONDITION_MAP.get(cleaned, PropertyCondition.GOOD)

    @classmethod
    def parse_and_validate(cls, raw_input: Dict[str, Any]) -> PropertyProfile:
        """Validate input payload and produce immutable, verified PropertyProfile."""
        # Check required fields
        if not raw_input.get("address"):
            raise ValueError("Property intake failed: 'address' is required.")
        if not raw_input.get("city"):
            raise ValueError("Property intake failed: 'city' is required.")
        if not raw_input.get("zip_code"):
            raise ValueError("Property intake failed: 'zip_code' is required.")

        try:
            sqft = float(raw_input["sqft"])
            if sqft <= 0:
                raise ValueError("sqft must be positive")
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Property intake failed: invalid or missing 'sqft': {e}")

        prop_id = str(raw_input.get("property_id") or f"PROP-{uuid.uuid4().hex[:8].upper()}")
        prop_type = cls.normalize_property_type(raw_input.get("property_type"))
        condition = cls.normalize_condition(raw_input.get("condition"))

        bedrooms = int(raw_input.get("bedrooms", 2))
        bathrooms = float(raw_input.get("bathrooms", 2.0))
        year_built = int(raw_input.get("year_built", 2018))
        lot_size = float(raw_input["lot_size_sqft"]) if raw_input.get("lot_size_sqft") else None
        amenities = [str(a).strip() for a in raw_input.get("amenities", []) if a]
        parking_spaces = int(raw_input.get("parking_spaces", 1))
        stories = int(raw_input.get("stories", 1))
        hoa = float(raw_input.get("hoa_monthly", 0.0))
        current_rent = float(raw_input["current_rent"]) if raw_input.get("current_rent") else None
        occupancy = float(raw_input["occupancy_rate"]) if raw_input.get("occupancy_rate") is not None else None

        origin = raw_input.get("data_origin", DataOrigin.USER_PROVIDED_DATA)
        if isinstance(origin, str):
            origin = DataOrigin(origin)

        provenance = ProvenanceMetadata(
            source=str(raw_input.get("source", "User Property Intake")),
            origin=origin,
            notice="User-provided property specifications for valuation.",
            record_id=prop_id,
        )

        return PropertyProfile(
            property_id=prop_id,
            address=str(raw_input["address"]).strip(),
            city=str(raw_input["city"]).strip(),
            state=str(raw_input.get("state", "TX")).strip().upper(),
            zip_code=str(raw_input["zip_code"]).strip(),
            property_type=prop_type,
            sqft=sqft,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            year_built=year_built,
            lot_size_sqft=lot_size,
            condition=condition,
            amenities=amenities,
            parking_spaces=parking_spaces,
            stories=stories,
            hoa_monthly=hoa,
            current_rent=current_rent,
            occupancy_rate=occupancy,
            data_origin=origin,
            provenance=provenance,
        )
