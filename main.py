import asyncio
from typing import Any

import pandas as pd

from app.data_models import (  # Import ManualHotelData
    ManualHotelData,
)
from app.prediction.price_model import (
    predict_price,  # Import predict_price
    train_advanced_price_prediction_model,
    train_price_prediction_model_without_high_level_data,
)
from app.scrapers.booking_com.main_scraper import (
    scrape_booking_com_data,
)
from app.utils.logger import logger


def get_manual_input(prompt: str, type_func: type, default: Any = None) -> Any:
    """Helper function to get validated manual input."""
    while True:
        user_input = input(f"{prompt} (default: {default}): ")
        if not user_input and default is not None:
            return default
        try:
            return type_func(user_input)
        except ValueError:
            print(f"Invalid input. Please enter a {type_func.__name__}.")


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


async def main():
    """Main function to run the scraper with user-provided values."""
    destination = "Unawatuna"
    adults = 2
    rooms = 1
    limit = 300
    hotel_details_limit = 100
    force_refetch = False

    # New configuration variables
    DATA_SOURCE = "scrape"  # Options: "scrape", "manual"
    PREDICTION_MODEL_TYPE = "basic"  # Options: "basic" ("low"), "advanced" ("high")
    TARGET_HOTEL_NAME: str | None = (
        "Sunset Mirage Villa Unawatuna"  # Set to None if no specific hotel is targeted (used only when DATA_SOURCE="scrape")
    )
    OUTPUT_SINGLE_AVERAGE_PRICE: bool = False  # Set to True to output a single average price for multiple predictions, or False to list all predictions

    logger.info("\nStarting process with parameters:")
    logger.debug(f"  Data Source: {DATA_SOURCE}")
    logger.debug(f"  Destination: {destination}")
    logger.debug(f"  Adults: {adults}")
    logger.debug(f"  Rooms: {rooms}")
    logger.debug(f"  Limit: {limit}")
    logger.debug(f"  Hotel Details Limit: {hotel_details_limit}")
    logger.debug(f"  Force Refetch: {force_refetch}")
    logger.debug(f"  Prediction Model Type: {PREDICTION_MODEL_TYPE}")
    if DATA_SOURCE == "scrape":
        logger.debug(f"  Target Hotel Name: {TARGET_HOTEL_NAME}")
    logger.info("-" * 30)

    try:
        # Initialize variables
        df_properties_for_training = None
        df_hotel_details_for_training = None
        df_properties_for_prediction = None
        df_hotel_details_for_prediction = None

        if DATA_SOURCE == "manual":
            # Step 1: Get manual input for YOUR villa (to predict)
            logger.info("Gathering manual hotel data from user (for prediction)...")
            (
                df_properties_for_prediction,
                df_hotel_details_for_prediction,
            ) = await get_manual_hotel_data_from_user()
            logger.success("Manual data entry successful!")

            # Step 2: Scrape OTHER properties from destination (for training)
            logger.info(f"Scraping properties from {destination} for model training...")
            # Determine hotel_details_limit based on model type
            scrape_hotel_details_limit = (
                0
                if PREDICTION_MODEL_TYPE.lower() in ["basic", "low"]
                else hotel_details_limit
            )

            (property_data, hotel_details_data) = await scrape_booking_com_data(
                destination=destination,
                adults=adults,
                rooms=rooms,
                limit=limit,
                hotel_details_limit=scrape_hotel_details_limit,
                force_refetch=force_refetch,
                target_hotel_name=None,  # Don't target specific hotel when scraping for training
            )
            logger.success(
                f"Scraping successful! Found {len(property_data)} properties for training."
            )

            df_properties_for_training = pd.DataFrame(property_data)
            df_hotel_details_for_training = pd.DataFrame(hotel_details_data)

        elif DATA_SOURCE == "scrape":
            # Scrape properties from destination
            logger.info(f"Scraping properties from {destination}...")
            # Determine hotel_details_limit based on model type
            scrape_hotel_details_limit = (
                0
                if PREDICTION_MODEL_TYPE.lower() in ["basic", "low"]
                else hotel_details_limit
            )

            (property_data, hotel_details_data) = await scrape_booking_com_data(
                destination=destination,
                adults=adults,
                rooms=rooms,
                limit=limit,
                hotel_details_limit=scrape_hotel_details_limit,
                force_refetch=force_refetch,
                target_hotel_name=TARGET_HOTEL_NAME,  # Target specific hotel if specified
            )
            logger.success(
                f"Scraping successful! Found {len(property_data)} properties."
            )

            df_properties_for_training = pd.DataFrame(property_data)
            df_hotel_details_for_training = pd.DataFrame(hotel_details_data)

            # For scrape mode, use the same data for prediction
            df_properties_for_prediction = df_properties_for_training.copy()
            df_hotel_details_for_prediction = df_hotel_details_for_training.copy()

        else:
            logger.error(
                f"Unknown DATA_SOURCE: {DATA_SOURCE}. Please choose 'scrape' or 'manual'."
            )
            return

        # Train selected model using training data
        if PREDICTION_MODEL_TYPE.lower() in ["advanced", "high"]:
            if not df_hotel_details_for_training.empty:
                logger.info("Training advanced price prediction model...")
                await train_advanced_price_prediction_model(
                    df_properties_for_training,
                    df_hotel_details_for_training,
                    destination=destination,
                    adults=adults,
                    rooms=rooms,
                    limit=limit,
                )
            else:
                logger.warning(
                    "Advanced model selected but no hotel details available. Falling back to basic model."
                )
                logger.info("Training basic price prediction model...")
                await train_price_prediction_model_without_high_level_data(
                    df_properties_for_training,
                    destination=destination,
                    adults=adults,
                    rooms=rooms,
                    limit=limit,
                )
        elif PREDICTION_MODEL_TYPE.lower() in ["basic", "low"]:
            logger.info("Training basic price prediction model...")
            await train_price_prediction_model_without_high_level_data(
                df_properties_for_training,
                destination=destination,
                adults=adults,
                rooms=rooms,
                limit=limit,
            )
        else:
            logger.warning(
                f"Unknown prediction model type '{PREDICTION_MODEL_TYPE}'. No model will be trained."
            )

        # --- Prediction using the trained model on prediction data ---
        logger.info("\n--- Making price predictions ---")
        if not df_properties_for_prediction.empty:
            predicted_prices_df = await predict_price(
                df_properties=df_properties_for_prediction,
                df_hotel_details=df_hotel_details_for_prediction
                if PREDICTION_MODEL_TYPE.lower() in ["advanced", "high"]
                else None,
                model_type=PREDICTION_MODEL_TYPE,
                destination=destination,
                adults=adults,
                rooms=rooms,
                limit=limit,
            )

            if not predicted_prices_df.empty:
                logger.success("Predicted prices:")
                if OUTPUT_SINGLE_AVERAGE_PRICE:
                    if len(predicted_prices_df) > 1:
                        avg_price = (
                            predicted_prices_df["predicted_price"].mean() / 2
                        )  # divide by 2 here
                        currency = predicted_prices_df["currency"].iloc[0]
                        print(f"- Average Price: {avg_price:.2f} {currency}")
                    else:
                        name = predicted_prices_df.iloc[0].get("name", "Property 1")
                        price = (
                            predicted_prices_df.iloc[0]["predicted_price"] / 2
                        )  # divide by 2 here
                        currency = predicted_prices_df.iloc[0]["currency"]
                        print(f"- {name}: {price:.2f} {currency}")
                else:
                    for index, row in predicted_prices_df.iterrows():
                        name = row.get("name", f"Property {index + 1}")
                        price = row["predicted_price"] / 2  # divide by 2 here
                        print(f"- {name}: {price:.2f} {row['currency']}")

            else:
                logger.warning("No predictions were generated.")
        else:
            logger.warning("No data available to make predictions.")

    except Exception as e:
        logger.error(f"An error occurred during the process: {e}")


if __name__ == "__main__":
    asyncio.run(main())
