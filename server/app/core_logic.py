import pandas as pd
from typing import Literal, Optional

from app.cli.manual_data_entry import get_manual_hotel_data_from_user
from app.prediction.model_predictor import predict_price
from app.scrapers.booking_com.orchestrator.scrape_booking_com_data import (
    scrape_booking_com_data,
)
from app.utils.logger import logger


async def run_prediction_flow(
    data_source: Literal["scrape", "manual"],
    destination: str,
    adults: int,
    rooms: int,
    properties_limit: int,
    hotel_details_limit: int,
    force_refetch: bool,
    prediction_model_type: Literal["basic", "advanced"],
    target_hotel_name: Optional[str] = None,
    manual_props_df: Optional[pd.DataFrame] = None,
    manual_details_df: Optional[pd.DataFrame] = None,
):
    """
    Core logic for both CLI and API to run the scraping and prediction process.
    """
    logger.info("\nStarting process with parameters:")
    logger.debug(f"  Data Source: {data_source}")
    logger.debug(f"  Destination: {destination}")
    logger.debug(f"  Adults: {adults}")
    logger.debug(f"  Rooms: {rooms}")
    logger.debug(f"  Properties Limit: {properties_limit}")
    logger.debug(f"  Hotel Details Limit: {hotel_details_limit}")
    logger.debug(f"  Force Refetch: {force_refetch}")
    logger.debug(f"  Prediction Model Type: {prediction_model_type}")

    user_df_properties: pd.DataFrame = pd.DataFrame()
    user_df_hotel_details: pd.DataFrame = pd.DataFrame()

    # --- Data Collection ---
    if data_source == "scrape":
        if not target_hotel_name:
            raise ValueError(
                "If using 'scrape' data source, 'target_hotel_name' is required."
            )
        logger.debug(f"  Target Hotel Name: {target_hotel_name}")
        logger.info("Scraping data from Booking.com...")
        (
            specific_property,
            specific_hotel_detail,
        ) = await scrape_booking_com_data(
            destination=destination,
            model_type=prediction_model_type,
            adults=adults,
            rooms=rooms,
            limit=properties_limit,
            hotel_details_limit=hotel_details_limit,
            force_refetch=force_refetch,
            target_hotel_name=target_hotel_name,
        )
        logger.info("Scraping complete.")
        if specific_property:
            user_df_properties = pd.DataFrame([specific_property.__dict__])
        if specific_hotel_detail:
            user_df_hotel_details = pd.DataFrame([specific_hotel_detail.__dict__])

    elif data_source == "manual":
        # For API, dataframes are passed in. For CLI, we use the interactive prompt.
        if manual_props_df is not None and manual_details_df is not None:
            user_df_properties = manual_props_df
            user_df_hotel_details = manual_details_df
        else:  # CLI case
            logger.info("Collecting manual hotel data for user's property...")
            (
                user_df_properties,
                user_df_hotel_details,
            ) = await get_manual_hotel_data_from_user()
            logger.info("Manual data collection complete.")

        # Still scrape general data for training even in manual mode
        logger.info("Scraping general data for training (even in manual mode)...")
        await scrape_booking_com_data(
            destination=destination,
            model_type=prediction_model_type,
            adults=adults,
            rooms=rooms,
            limit=properties_limit,
            hotel_details_limit=hotel_details_limit,
            force_refetch=force_refetch,
            target_hotel_name=None,  # No specific target
        )
        logger.info("General data scraping complete.")

    # --- Price Prediction ---
    if user_df_properties.empty:
        logger.warning(
            "No data available for price prediction for the user's property."
        )
        return None

    logger.info("Predicting prices...")
    try:
        predicted_prices_df = await predict_price(
            df_properties=user_df_properties,
            df_hotel_details=user_df_hotel_details,
            model_type=prediction_model_type,
            destination=destination,
            adults=adults,
            rooms=rooms,
            limit=properties_limit,
            hotel_details_limit=hotel_details_limit,
        )
        logger.info("Price prediction successful!")
        logger.info("\n--- Predicted Prices ---")
        logger.info(predicted_prices_df.to_string())
        logger.info("------------------------")
        return predicted_prices_df

    except FileNotFoundError as e:
        logger.error(f"Prediction model not found. Error: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred during price prediction: {e}", exc_info=True)
        raise
