"""Property selector component with pre-loaded Indian demo fixtures and custom intake form."""

from typing import Any, Dict

import streamlit as st
from src.core.formatters import format_bhk, format_inr, format_rent

DEMO_PROPERTIES: Dict[str, Dict[str, Any]] = {
    "Hyderabad HITEC City / Gachibowli (PROP-HYD-001)": {
        "property_id": "PROP-HYD-001",
        "address": "Tower 4, My Home Bhooja, Silpa Gram, HITEC City",
        "city": "Hyderabad",
        "state": "Telangana",
        "zip_code": "500081",
        "locality": "HITEC City / Gachibowli",
        "property_type": "Apartment",
        "sqft": 1850.0,
        "carpet_area_sqft": 1450.0,
        "bedrooms": 3,
        "bathrooms": 3.0,
        "year_built": 2021,
        "condition": "Excellent",
        "amenities": ["Clubhouse", "Swimming Pool", "Gym", "Power Backup", "Covered Parking", "24/7 Security", "Balcony"],
        "parking_spaces": 2,
        "current_rent": 65000.0,
        "source": "Pre-loaded Hyderabad Demonstration Fixture",
    },
    "Bengaluru Whitefield IT Corridor (PROP-BLR-001)": {
        "property_id": "PROP-BLR-001",
        "address": "Prestige Shantiniketan, Tower 12, ITPL Main Rd, Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "zip_code": "560066",
        "locality": "Whitefield",
        "property_type": "Apartment",
        "sqft": 1650.0,
        "carpet_area_sqft": 1300.0,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "year_built": 2019,
        "condition": "Good",
        "amenities": ["Clubhouse", "Gym", "Swimming Pool", "Covered Parking", "Power Backup", "Balcony"],
        "parking_spaces": 1,
        "current_rent": 52000.0,
        "source": "Pre-loaded Bengaluru Demonstration Fixture",
    },
    "Mumbai Powai Hiranandani High-Rise (PROP-BOM-001)": {
        "property_id": "PROP-BOM-001",
        "address": "Hiranandani Gardens, Castle Rock, Powai",
        "city": "Mumbai",
        "state": "Maharashtra",
        "zip_code": "400076",
        "locality": "Powai",
        "property_type": "Apartment",
        "sqft": 1250.0,
        "carpet_area_sqft": 950.0,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "year_built": 2020,
        "condition": "LuxuryRenovated",
        "amenities": ["Gym", "Clubhouse", "Lake View", "Concierge", "Covered Parking", "Power Backup"],
        "parking_spaces": 1,
        "current_rent": 78000.0,
        "source": "Pre-loaded Mumbai Demonstration Fixture",
    },
    "Pune Baner Premium Gated Community (PROP-PUN-001)": {
        "property_id": "PROP-PUN-001",
        "address": "Kasturi The Balmoral Riverside, Baner",
        "city": "Pune",
        "state": "Maharashtra",
        "zip_code": "411045",
        "locality": "Baner",
        "property_type": "Apartment",
        "sqft": 1400.0,
        "carpet_area_sqft": 1100.0,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "year_built": 2022,
        "condition": "Excellent",
        "amenities": ["Gym", "Clubhouse", "Swimming Pool", "Covered Parking", "EV Charging"],
        "parking_spaces": 1,
        "current_rent": 38000.0,
        "source": "Pre-loaded Pune Demonstration Fixture",
    },
    "Visakhapatnam Rushikonda Coastal Villa (PROP-VTZ-001)": {
        "property_id": "PROP-VTZ-001",
        "address": "Hill View Enclave, Rushikonda IT SEZ Road",
        "city": "Visakhapatnam",
        "state": "Andhra Pradesh",
        "zip_code": "530045",
        "locality": "Rushikonda",
        "property_type": "Villa",
        "sqft": 2400.0,
        "carpet_area_sqft": 2050.0,
        "bedrooms": 4,
        "bathrooms": 4.0,
        "year_built": 2021,
        "condition": "Excellent",
        "amenities": ["Private Garden", "Sea View", "Covered Parking", "Power Backup", "24/7 Security"],
        "parking_spaces": 2,
        "current_rent": 48000.0,
        "source": "Pre-loaded Visakhapatnam Demonstration Fixture",
    },
}

# Backward compatibility alias for tests referencing Austin demo key
DEMO_PROPERTIES["Austin Downtown Luxury Condo (PROP-ATX-001)"] = {
    "property_id": "PROP-ATX-001",
    "address": "1208 Colorado St #4B",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "locality": "Downtown Austin",
    "property_type": "Condo",
    "sqft": 1150.0,
    "carpet_area_sqft": 900.0,
    "bedrooms": 2,
    "bathrooms": 2.0,
    "year_built": 2019,
    "condition": "Excellent",
    "amenities": ["Pool", "Gym", "Concierge", "Balcony"],
    "parking_spaces": 1,
    "current_rent": 65000.0,
    "source": "Pre-loaded Austin Demonstration Fixture (Compatibility Alias)",
}


def render_property_selector() -> Dict[str, Any]:
    """Render property selection controls in the sidebar."""
    st.sidebar.markdown("### 🏢 Property Selection")

    mode = st.sidebar.radio(
        "Input Mode",
        ["Select Demonstration Property", "Enter Custom Property"],
        index=0,
    )

    # Exclude compatibility alias from primary user UI selectbox
    ui_options = [k for k in DEMO_PROPERTIES.keys() if "PROP-ATX-001" not in k]

    if mode == "Select Demonstration Property":
        chosen_name = st.sidebar.selectbox(
            "Choose Demonstration Asset",
            ui_options,
        )
        selected_data = DEMO_PROPERTIES[chosen_name].copy()
        locality_str = f" · {selected_data.get('locality')}" if selected_data.get("locality") else ""
        bhk_str = format_bhk(selected_data['bedrooms'])
        rent_display = format_rent(selected_data['current_rent']) if selected_data.get('current_rent') else "N/A"
        st.sidebar.info(
            f"📍 **{selected_data['address']}**\n\n"
            f"**{bhk_str}** ({selected_data['bathrooms']:.0f} Bath) · {selected_data['sqft']:,.0f} sq ft built-up{locality_str}\n\n"
            f"PIN: {selected_data['zip_code']} · In-Place Rent: **{rent_display}**"
        )
        return selected_data

    else:
        st.sidebar.markdown("#### Custom Property Intake")
        address = st.sidebar.text_input("Society / Building & Flat", value="Tower 2, Flat 1402, Gachibowli")
        locality = st.sidebar.text_input("Locality / Sector", value="Gachibowli")

        city = st.sidebar.selectbox(
            "City",
            ["Hyderabad", "Bengaluru", "Mumbai", "Pune", "Visakhapatnam", "Delhi NCR", "Chennai"],
        )
        state_map = {
            "Hyderabad": "Telangana",
            "Bengaluru": "Karnataka",
            "Mumbai": "Maharashtra",
            "Pune": "Maharashtra",
            "Visakhapatnam": "Andhra Pradesh",
            "Delhi NCR": "Haryana",
            "Chennai": "Tamil Nadu",
        }
        pin_map = {
            "Hyderabad": "500081",
            "Bengaluru": "560066",
            "Mumbai": "400076",
            "Pune": "411045",
            "Visakhapatnam": "530045",
            "Delhi NCR": "122002",
            "Chennai": "600096",
        }

        pin_code = st.sidebar.text_input("PIN Code", value=pin_map.get(city, "500081"))

        prop_type_labels = {
            "Apartment": "Apartment / Flat",
            "IndependentHouse": "Independent House / Villa",
            "Villa": "Villa / Row House",
            "Commercial": "Commercial Office / Retail",
        }
        prop_type_key = st.sidebar.selectbox(
            "Property Type",
            list(prop_type_labels.keys()),
            format_func=lambda k: prop_type_labels[k],
        )

        condition = st.sidebar.selectbox(
            "Property Condition",
            ["Excellent", "Good", "LuxuryRenovated", "Fair", "Poor"],
        )

        col1, col2 = st.sidebar.columns(2)
        with col1:
            sqft = st.number_input("Super Built-up Area (Sq Ft)", value=1850.0, min_value=300.0, step=50.0)
            bedrooms = st.number_input("Bedrooms (BHK)", value=3, min_value=0, step=1)
        with col2:
            bathrooms = st.number_input("Bathrooms", value=3.0, min_value=1.0, step=0.5)
            year_built = st.number_input("Year Built", value=2021, min_value=1950, max_value=2026, step=1)

        carpet_area = st.sidebar.number_input(
            "RERA Carpet Area (Sq Ft, optional)",
            value=round(sqft * 0.78, 0),
            min_value=0.0,
            step=25.0,
        )

        current_rent = st.sidebar.number_input(
            "Current In-Place Rent (₹/month, optional)",
            value=60000.0,
            min_value=0.0,
            step=1000.0,
        )

        amenities = st.sidebar.multiselect(
            "Key Amenities & Facilities",
            [
                "Clubhouse",
                "Swimming Pool",
                "Gym",
                "Covered Parking",
                "Power Backup",
                "24/7 Security",
                "Gated Community",
                "Balcony",
                "EV Charging",
                "Private Garden",
                "Gas Pipeline",
                "Children Play Area",
            ],
            default=["Clubhouse", "Gym", "Covered Parking", "Power Backup", "Balcony"],
        )

        parking_spaces = st.sidebar.number_input("Reserved Car Parking Spaces", value=2, min_value=0, step=1)

        return {
            "property_id": "PROP-CUSTOM-USER",
            "address": address,
            "locality": locality,
            "city": city,
            "state": state_map.get(city, "Telangana"),
            "zip_code": pin_code,
            "pin_code": pin_code,
            "property_type": prop_type_key,
            "sqft": sqft,
            "carpet_area_sqft": carpet_area if carpet_area > 0 else None,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "year_built": year_built,
            "condition": condition,
            "amenities": amenities,
            "parking_spaces": parking_spaces,
            "current_rent": current_rent if current_rent > 0 else None,
            "source": "Custom Indian Property Intake Form",
        }
