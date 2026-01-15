import argparse

import pandas as pd

from app.cli.manual_data_entry import get_manual_hotel_data_from_user
from app.data_models import HotelDetails, PropertyListing
from app.prediction.model_loader import load_model_artifacts  # To check if model exists
from app.prediction.model_predictor import predict_price
from app.prediction.training.advanced_trainer import train_advanced_model
from app.prediction.training.basic_trainer import train_model
from app.scrapers.booking_com.orchestrator import scrape_booking_com_data
from app.utils.logger import logger


async def main():
    """Main function to run the scraper with user-provided values."""
    parser = argparse.ArgumentParser(
        description="Run the Ez-Rent scraper and prediction."
    )

    parser.add_argument(
        "--destination",
        type=str,
        default="Unawatuna",
        help="Destination for scraping (e.g., city, region).",
    )
    parser.add_argument(
        "--adults", type=int, default=2, help="Number of adults for the booking."
    )
    parser.add_argument(
        "--rooms", type=int, default=1, help="Number of rooms for the booking."
    )
    parser.add_argument(
        "--limit", type=int, default=300, help="Maximum number of properties to scrape."
    )
    parser.add_argument(
        "--hotel_details_limit",
        type=int,
        default=100,
        help="Maximum number of hotel details to scrape.",
    )
    parser.add_argument(
        "--force_refetch",
        action="store_true",
        help="If set, forces refetching of data even if cached.",
    )
    parser.add_argument(
        "--data_source",
        type=str,
        choices=["scrape", "manual"],
        default="scrape",
        help="Source of data: 'scrape' from Booking.com or 'manual' entry.",
    )
    parser.add_argument(
        "--prediction_model_type",
        type=str,
        choices=["basic", "advanced"],
        default="basic",
        help="Type of prediction model to use: 'basic' or 'advanced'.",
    )
    parser.add_argument(
        "--target_hotel_name",
        type=str,
        default="Sunset Mirage Villa",
        help="Specific hotel name to target during scraping. Only used when data_source is 'scrape'.",
    )

    args = parser.parse_args()

    destination = args.destination
    adults = args.adults
    rooms = args.rooms
    limit = args.limit
    hotel_details_limit = args.hotel_details_limit
    force_refetch = args.force_refetch

    DATA_SOURCE = args.data_source
    PREDICTION_MODEL_TYPE = args.prediction_model_type
    TARGET_HOTEL_NAME = args.target_hotel_name

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
    logger.info("---")

    user_df_properties: pd.DataFrame = pd.DataFrame()
    user_df_hotel_details: pd.DataFrame = pd.DataFrame()
    general_df_properties: pd.DataFrame = pd.DataFrame()
    general_df_hotel_details: pd.DataFrame = pd.DataFrame()

    # --- Data Collection ---
    if DATA_SOURCE == "scrape":
        logger.info("Scraping data from Booking.com...")
        (
            specific_property,
            specific_hotel_detail,
            general_df_properties,
            general_df_hotel_details,
        ) = await scrape_booking_com_data(
            destination=destination,
            model_type=PREDICTION_MODEL_TYPE,
            adults=adults,
            rooms=rooms,
            limit=limit,
            hotel_details_limit=hotel_details_limit,
            force_refetch=force_refetch,
            target_hotel_name=TARGET_HOTEL_NAME,
        )
        logger.info("Scraping complete.")

        if specific_property:
            user_df_properties = pd.DataFrame([specific_property.__dict__])
            logger.debug(
                f"User Property Listing (specific_property): {specific_property}"
            )
        else:
            logger.debug("Specific property not found or scraped.")

        if specific_hotel_detail:
            user_df_hotel_details = pd.DataFrame([specific_hotel_detail.__dict__])
            logger.debug(
                f"User Hotel Details (specific_hotel_detail): {specific_hotel_detail}"
            )
        else:
            logger.debug("Specific hotel details not found or scraped.")

        logger.debug(
            f"User df_properties after scrape: {len(user_df_properties)} rows."
        )
        logger.debug(
            f"User df_hotel_details after scrape: {len(user_df_hotel_details)} rows."
        )

    elif DATA_SOURCE == "manual":
        logger.info("Collecting manual hotel data for user's property...")
        (
            user_df_properties,
            user_df_hotel_details,
        ) = await get_manual_hotel_data_from_user()
        logger.info("Manual data collection complete.")
        logger.debug(
            f"User df_properties after manual input: {len(user_df_properties)} rows."
        )
        logger.debug(
            f"User df_hotel_details after manual input: {len(user_df_hotel_details)} rows."
        )

        # Still scrape general data for training even in manual mode
        logger.info("Scraping general data for training (even in manual mode)...")
        (
            _,  # specific_property is not relevant here
            _,  # specific_hotel_detail is not relevant here
            general_df_properties,
            general_df_hotel_details,
        ) = await scrape_booking_com_data(
            destination=destination,
            model_type=PREDICTION_MODEL_TYPE,
            adults=adults,
            rooms=rooms,
            limit=limit,
            hotel_details_limit=hotel_details_limit,
            force_refetch=force_refetch,
            target_hotel_name=None,  # Ensure no specific hotel is targeted for general scrape
        )
        logger.info("General data scraping complete.")

    # --- Price Prediction ---
    if not user_df_properties.empty:
        logger.info("Predicting prices...")
        try:
            predicted_prices_df = await predict_price(
                df_properties=user_df_properties,
                df_hotel_details=user_df_hotel_details,
                model_type=PREDICTION_MODEL_TYPE,
                destination=destination,
                adults=adults,
                rooms=rooms,
                limit=limit,
                hotel_details_limit=hotel_details_limit, # New parameter
            )
            logger.info("Price prediction successful!")
            logger.info("\n--- Predicted Prices ---")
            logger.info(predicted_prices_df.to_string())
            logger.info("------------------------")
        except FileNotFoundError as e:
            logger.error(
                f"Prediction model not found. This should not happen if training was just completed or model existed. Error: {e}"
            )
        except Exception as e:
            logger.error(
                f"An error occurred during price prediction: {e}", exc_info=True
            )
    else:
        logger.warning(
            "No data available for price prediction for the user's property."
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
