"""Property selector component with pre-loaded demo fixtures and custom intake form."""

from typing import Any, Dict

import streamlit as st

DEMO_PROPERTIES: Dict[str, Dict[str, Any]] = {
    "Austin Downtown Luxury Condo (PROP-ATX-001)": {
        "property_id": "PROP-ATX-001",
        "address": "1208 Colorado St #4B",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "property_type": "Condo",
        "sqft": 1150.0,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "year_built": 2019,
        "condition": "Excellent",
        "amenities": ["Pool", "Gym", "Concierge", "Balcony"],
        "parking_spaces": 1,
        "current_rent": 3050.0,
        "source": "Pre-loaded Austin Demonstration Fixture",
    },
    "Seattle Capitol Hill Urban Townhome (PROP-SEA-001)": {
        "property_id": "PROP-SEA-001",
        "address": "402 E Roy St #304",
        "city": "Seattle",
        "state": "WA",
        "zip_code": "98102",
        "property_type": "Condo",
        "sqft": 1100.0,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "year_built": 2016,
        "condition": "Excellent",
        "amenities": ["Rooftop Deck", "Secured Parking", "Storage"],
        "parking_spaces": 1,
        "current_rent": 3350.0,
        "source": "Pre-loaded Seattle Demonstration Fixture",
    },
    "Miami Brickell Bay Luxury Tower (PROP-MIA-001)": {
        "property_id": "PROP-MIA-001",
        "address": "1100 Brickell Bay Dr #18B",
        "city": "Miami",
        "state": "FL",
        "zip_code": "33131",
        "property_type": "Condo",
        "sqft": 1150.0,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "year_built": 2018,
        "condition": "LuxuryRenovated",
        "amenities": ["Infinity Pool", "Bay Views", "Valet", "Spa", "Gym"],
        "parking_spaces": 1,
        "current_rent": 4150.0,
        "source": "Pre-loaded Miami Demonstration Fixture",
    },
}


def render_property_selector() -> Dict[str, Any]:
    """Render property selection controls in the sidebar."""
    st.sidebar.markdown("### 🏢 Property Selection")

    mode = st.sidebar.radio(
        "Input Mode",
        ["Select Demonstration Property", "Enter Custom Property"],
        index=0,
    )

    if mode == "Select Demonstration Property":
        chosen_name = st.sidebar.selectbox(
            "Choose Demonstration Asset",
            list(DEMO_PROPERTIES.keys()),
        )
        selected_data = DEMO_PROPERTIES[chosen_name].copy()
        st.sidebar.info(
            f"📍 **{selected_data['address']}**\n\n"
            f"{selected_data['bedrooms']} Bed · {selected_data['bathrooms']} Bath · {selected_data['sqft']:,.0f} sqft\n\n"
            f"Type: {selected_data['property_type']} ({selected_data['condition']})"
        )
        return selected_data

    else:
        st.sidebar.markdown("#### Custom Property Intake")
        address = st.sidebar.text_input("Street Address", value="500 S Congress Ave")
        city = st.sidebar.selectbox("City", ["Austin", "Seattle", "Miami"])
        state_map = {"Austin": "TX", "Seattle": "WA", "Miami": "FL"}
        zip_map = {"Austin": "78701", "Seattle": "98102", "Miami": "33131"}

        prop_type = st.sidebar.selectbox("Property Type", ["Condo", "SingleFamily", "Townhouse", "MultiFamily"])
        condition = st.sidebar.selectbox("Condition", ["Excellent", "Good", "LuxuryRenovated", "Fair", "Poor"])

        col1, col2 = st.sidebar.columns(2)
        with col1:
            sqft = st.number_input("Living Area (SqFt)", value=1150.0, min_value=300.0, step=50.0)
            bedrooms = st.number_input("Bedrooms", value=2, min_value=0, step=1)
        with col2:
            bathrooms = st.number_input("Bathrooms", value=2.0, min_value=1.0, step=0.5)
            year_built = st.number_input("Year Built", value=2019, min_value=1900, max_value=2026, step=1)

        current_rent = st.sidebar.number_input("Current Rent ($/mo, optional)", value=3000.0, min_value=0.0, step=50.0)
        amenities = st.sidebar.multiselect(
            "Key Amenities",
            ["Pool", "Gym", "Concierge", "Balcony", "Rooftop Deck", "Valet", "EV Charging", "Storage"],
            default=["Pool", "Gym", "Balcony"],
        )

        return {
            "property_id": "PROP-CUSTOM-USER",
            "address": address,
            "city": city,
            "state": state_map[city],
            "zip_code": zip_map[city],
            "property_type": prop_type,
            "sqft": sqft,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "year_built": year_built,
            "condition": condition,
            "amenities": amenities,
            "parking_spaces": 1,
            "current_rent": current_rent if current_rent > 0 else None,
            "source": "Custom User Input Form",
        }
