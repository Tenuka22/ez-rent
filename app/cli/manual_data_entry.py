import pandas as pd
from typing import Any, Tuple

from app.data_models import ManualHotelData
from app.cli.input_utils import get_manual_input
from app.utils.logger import logger


async def get_manual_hotel_data_from_user() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prompts the user to manually enter hotel data and returns it as DataFrames.
    """
    logger.info("Starting manual data entry for hotel features.")

    manual_data = ManualHotelData(
        name=get_manual_input(
            "Enter Hotel Name (e.g., Grand Hyatt)", str, "Manual Entry Hotel"
        ),
        hotel_link=get_manual_input(
            "Enter Hotel Link (e.g., http://example.com/hotel)",
            str,
            "http://manual.entry.com",
        ),
        star_rating=get_manual_input("Enter Star Rating (e.g., 3.5)", float, 0.0),
        guest_rating_score=get_manual_input(
            "Enter Guest Rating Score (e.g., 8.5)", float, 0.0
        ),
        reviews=get_manual_input("Enter Number of Reviews (e.g., 250)", float, 0.0),
        distance_from_downtown=get_manual_input(
            "Enter Distance from Downtown in km (e.g., 2.5)", float, 0.0
        ),
        distance_from_beach=get_manual_input(
            "Enter Distance from Beach in km (e.g., 0.3)", float, 0.0
        ),
        preferred_badge=get_manual_input(
            "Has Preferred Badge? (1 for Yes, 0 for No)", int, 0
        ),
        has_pool=get_manual_input("Has Pool? (1 for Yes, 0 for No)", int, 0),
        has_free_wifi=get_manual_input("Has Free WiFi? (1 for Yes, 0 for No)", int, 0),
        has_free_parking=get_manual_input(
            "Has Free Parking? (1 for Yes, 0 for No)", int, 0
        ),
        has_spa=get_manual_input("Has Spa? (1 for Yes, 0 for No)", int, 0),
        description_length=get_manual_input(
            "Enter Description Length (approx. number of characters)", int, 0
        ),
        num_popular_facilities=get_manual_input(
            "Enter Number of Popular Facilities", int, 0
        ),
        num_languages_spoken=get_manual_input(
            "Enter Number of Languages Spoken", int, 0
        ),
        has_restaurant=get_manual_input(
            "Has Restaurant? (1 for Yes, 0 for No)", int, 0
        ),
        has_bar=get_manual_input("Has Bar? (1 for Yes, 0 for No)", int, 0),
        has_breakfast=get_manual_input("Has Breakfast? (1 for Yes, 0 for No)", int, 0),
        has_room_service=get_manual_input(
            "Has Room Service? (1 for Yes, 0 for No)", int, 0
        ),
        has_24hr_front_desk=get_manual_input(
            "Has 24hr Front Desk? (1 for Yes, 0 for No)", int, 0
        ),
        has_airport_shuttle=get_manual_input(
            "Has Airport Shuttle? (1 for Yes, 0 for No)", int, 0
        ),
        has_family_rooms=get_manual_input(
            "Has Family Rooms? (1 for Yes, 0 for No)", int, 0
        ),
        has_air_conditioning_detail=get_manual_input(
            "Has Air Conditioning? (1 for Yes, 0 for No)", int, 0
        ),
        has_non_smoking_rooms=get_manual_input(
            "Has Non-Smoking Rooms? (1 for Yes, 0 for No)", int, 0
        ),
        has_private_bathroom=get_manual_input(
            "Has Private Bathroom? (1 for Yes, 0 for No)", int, 0
        ),
        has_kitchenette=get_manual_input(
            "Has Kitchenette? (1 for Yes, 0 for No)", int, 0
        ),
        has_balcony=get_manual_input("Has Balcony? (1 for Yes, 0 for No)", int, 0),
        has_terrace=get_manual_input("Has Terrace? (1 for Yes, 0 for No)", int, 0),
        discounted_price_currency=get_manual_input(
            "Enter Currency (e.g., LKR, USD)", str, "LKR"
        ),
    )

    logger.info("Manual data entry complete.")

    # Convert manual_data to DataFrames mimicking scraped data structure
    df_properties = pd.DataFrame(
        [manual_data.__dict__]
    )  # Simple conversion, may need more specific mapping

    # Create a df_hotel_details that is compatible with _extract_hotel_details_features
    df_hotel_details = pd.DataFrame(
        [
            {
                "url": manual_data.hotel_link,
                "name": manual_data.name,
                "star_rating": manual_data.star_rating,
                "guest_rating": manual_data.guest_rating_score,
                "review_count": manual_data.reviews,
                "description": "Manual entry description for "
                + manual_data.name
                + ". "
                * (
                    manual_data.description_length // 20 + 1
                ),  # Approximate length for feature extraction
                "most_popular_facilities": ["Pool"]
                if manual_data.has_pool
                else (
                    ["Free WiFi"]
                    if manual_data.has_free_wifi
                    else (["Free parking"] if manual_data.has_free_parking else [])
                ),  # Simplified popular facilities
                "bathroom_facilities": ["Private bathroom"]
                if manual_data.has_private_bathroom
                else [],
                "view_type": [],  # Not directly from manual input
                "outdoor_facilities": (["Balcony"] if manual_data.has_balcony else [])
                + (["Terrace"] if manual_data.has_terrace else []),
                "kitchen_facilities": ["Kitchenette"]
                if manual_data.has_kitchenette
                else [],
                "room_amenities": ["Air conditioning"]
                if manual_data.has_air_conditioning_detail
                else (
                    ["Non-smoking rooms"] if manual_data.has_non_smoking_rooms else []
                ),
                "activities": ["Spa"] if manual_data.has_spa else [],
                "food_drink": (["Restaurant"] if manual_data.has_restaurant else [])
                + (["Bar"] if manual_data.has_bar else [])
                + (["Breakfast"] if manual_data.has_breakfast else []),
                "internet_info": "Free WiFi" if manual_data.has_free_wifi else None,
                "parking_info": "Free parking"
                if manual_data.has_free_parking
                else None,
                "services": (["Room service"] if manual_data.has_room_service else [])
                + (["24-hour front desk"] if manual_data.has_24hr_front_desk else []),
                "safety_security": [],  # Not directly from manual input
                "general_facilities": (
                    (["Airport shuttle"] if manual_data.has_airport_shuttle else [])
                    + (["Family rooms"] if manual_data.has_family_rooms else [])
                    + (
                        ["Non-smoking rooms"]
                        if manual_data.has_non_smoking_rooms
                        else []
                    )
                ),
                "pool_info": {"type": "Outdoor swimming pool", "free": True}
                if manual_data.has_pool
                else None,
                "spa_wellness": ["Spa"] if manual_data.has_spa else [],
                "languages_spoken": ["English"]
                * manual_data.num_languages_spoken,  # Simplified
                "property_highlights": [],  # Not directly from manual input
                # Other HotelDetails fields will be None or default as they are not manual inputs
                "address": None,
                "coordinates": None,
                "location_score": None,
                "review_score_text": None,
            }
        ]
    )

    # Add currency column to df_properties for consistency, as it's needed for the model
    df_properties["discounted_price_currency"] = manual_data.discounted_price_currency

    return df_properties, df_hotel_details