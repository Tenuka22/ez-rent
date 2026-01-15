import argparse

import pandas as pd

from app.cli.manual_data_entry import get_manual_hotel_data_from_user
from app.prediction.model_predictor import predict_price
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
        default=None,
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

    df_properties: pd.DataFrame = pd.DataFrame()
    df_hotel_details: pd.DataFrame = pd.DataFrame()

    if DATA_SOURCE == "scrape":
        logger.info("Scraping data from Booking.com...")
        df_properties, df_hotel_details = await scrape_booking_com_data(
            destination=destination,
            adults=adults,
            rooms=rooms,
            limit=limit,
            hotel_details_limit=hotel_details_limit,
            force_refetch=force_refetch,
            target_hotel_name=TARGET_HOTEL_NAME,
        )
        logger.info("Scraping complete.")
    elif DATA_SOURCE == "manual":
        logger.info("Collecting manual hotel data...")
        df_properties, df_hotel_details = await get_manual_hotel_data_from_user()
        logger.info("Manual data collection complete.")

    if not df_properties.empty:
        logger.info("Predicting prices...")
        try:
            predicted_prices_df = await predict_price(
                df_properties=df_properties,
                df_hotel_details=df_hotel_details,
                model_type=PREDICTION_MODEL_TYPE,
                destination=destination,
                adults=adults,
                rooms=rooms,
                limit=limit,
            )
            logger.info("Price prediction successful!")
            logger.info("\n--- Predicted Prices ---")
            logger.info(predicted_prices_df.to_string())
            logger.info("------------------------")
        except FileNotFoundError as e:
            logger.error(
                f"Prediction model not found. Please train the '{PREDICTION_MODEL_TYPE}' "
                f"model for '{destination}' with adults={adults}, rooms={rooms}, limit={limit} first. Error: {e}"
            )
        except Exception as e:
            logger.error(
                f"An error occurred during price prediction: {e}", exc_info=True
            )
    else:
        logger.warning("No data available for price prediction.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
