import asyncio
import os
import argparse
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
from playwright.async_api import Browser, Page, async_playwright

from app.data_models import HotelDetails, PropertyListing
from app.prediction.model_utils.save_model_metadata import save_model_metadata
from app.prediction.model_utils.should_retrain_model import should_retrain_model
from app.prediction.training.basic_trainer import train_model
from app.scrapers.booking_com.extractors.specific_property_extractor import (
    scrape_specific_property_data,
)
from app.scrapers.booking_com.orchestrator.scrape_general_data import (
    scrape_general_data,
)
from app.utils.constants import (
    get_model_filepath,
)
from app.utils.logger import logger


async def scrape_booking_com_data(
    destination: str,
    model_type: str = "basic",
    hotel_details_limit: int = 10,
    adults: int = 2,
    rooms: int = 1,
    limit: int = 100,
    force_refetch: bool = False,
    target_hotel_name: Optional[str] = None,
    force_fetch_delay: Optional[timedelta] = None,
) -> Tuple[
    Optional[PropertyListing],
    Optional[HotelDetails],
]:
    """
    Orchestrates the scraping of Booking.com data, including general properties and
    optionally a specific target hotel, and handles model retraining.

    Args:
        destination (str): The destination (city, region) for scraping.
        model_type (str): The type of model to use ('basic' or 'advanced'). Defaults to "basic".
        hotel_details_limit (int): Maximum number of hotel details to scrape. Defaults to 10.
        adults (int): Number of adults for the booking. Defaults to 2.
        rooms (int): Number of rooms for the booking. Defaults to 1.
        limit (int): Maximum number of properties to scrape. Defaults to 100.
        force_refetch (bool): If True, forces refetching of data even if cached. Defaults to False.
        target_hotel_name (Optional[str]): Specific hotel name to target during scraping. Defaults to None.
        force_fetch_delay (Optional[timedelta]): Delay to force refetching after. Defaults to None (7 days).

    Returns:
        Tuple[Optional[PropertyListing], Optional[HotelDetails]]:
            A tuple containing the PropertyListing and HotelDetails for the specific target hotel,
            or (None, None) if no target hotel was specified or found.
    """
    logger.debug(f"hotel_details_limit received: {hotel_details_limit}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        specific_property: Optional[PropertyListing] = None
        specific_hotel_detail: Optional[HotelDetails] = None

        try:
            if target_hotel_name:
                logger.info(f"Attempting to scrape specific hotel: {target_hotel_name}")
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                try:
                    (
                        specific_property,
                        specific_hotel_detail,
                    ) = await scrape_specific_property_data(
                        page, adults, rooms, target_hotel_name
                    )
                    logger.success(
                        f"Successfully scraped specific property: {target_hotel_name}"
                    )
                finally:
                    await page.close()
                    await context.close()

            # --- Scrape general properties and details (excluding the specific one if found) ---
            (
                general_df_properties,
                general_df_hotel_details,
            ) = await scrape_general_data(
                browser,
                destination,
                hotel_details_limit,
                adults,
                rooms,
                limit,
                force_refetch,
                specific_property_to_exclude=specific_property,
                force_fetch_delay=force_fetch_delay,
            )

            # --- Dynamic Model Training ---
            model_filepath = get_model_filepath(
                destination,
                adults,
                rooms,
                limit,
                hotel_details_limit,
                model_name=f"{model_type}_price_predictor",
            )

            if should_retrain_model(
                model_filepath,
                len(general_df_properties),
                len(general_df_hotel_details),
            ):
                logger.info(f"Retraining model '{model_filepath}' is recommended.")

                if (
                    not force_refetch
                ):  # Only force refetch if it wasn't already requested
                    logger.info("Forcing refetch of general data for model retraining.")
                    (
                        general_df_properties,
                        general_df_hotel_details,
                    ) = await scrape_general_data(
                        browser,
                        destination,
                        hotel_details_limit,
                        adults,
                        rooms,
                        limit,
                        force_refetch=force_refetch,
                        specific_property_to_exclude=specific_property,
                        force_fetch_delay=force_fetch_delay,
                    )
                else:
                    logger.info(
                        "General data already refetched due to --force_refetch flag."
                    )

                logger.info(f"Initiating retraining for model '{model_filepath}'...")
                # Assuming train_model in basic_trainer takes properties_df and hotel_details_df
                await train_model(
                    general_df_properties,  # Use the potentially refetched data
                    general_df_hotel_details,  # Use the potentially refetched data
                    destination,
                    adults,
                    rooms,
                    limit,
                    hotel_details_limit,
                    model_filepath,
                )
                # Save new metadata based on the data actually used for training
                metadata = {
                    "last_trained_at": datetime.now().isoformat(),
                    "trained_properties_count": len(general_df_properties),
                    "trained_hotel_details_count": len(general_df_hotel_details),
                }
                # Extract the base name from the full model_filepath for metadata saving
               
                save_model_metadata(model_filename=model_filepath,metadata=metadata)
                logger.success(
                    f"Model '{model_filepath}' retrained and metadata updated."
                )
            else:
                logger.info(
                    f"Model '{model_filepath}' is up-to-date. Skipping retraining."
                )

        except Exception as e:
            logger.error(f"Error during scraping process: {e}", exc_info=True)
            raise
        finally:
            await browser.close()

    return (
        specific_property,
        specific_hotel_detail,
    )


if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Booking.com data and train model.")
    parser.add_argument("--destination", type=str, default="Unawatuna", help="Destination to scrape (e.g., 'Unawatuna').")
    parser.add_argument("--adults", type=int, default=2, help="Number of adults.")
    parser.add_argument("--rooms", type=int, default=1, help="Number of rooms.")
    parser.add_argument("--limit", type=int, default=300, help="Maximum number of properties to scrape.")
    parser.add_argument("--hotel_details_limit", type=int, default=100, help="Maximum number of hotel details to scrape.")
    parser.add_argument("--model_type", type=str, default="basic", choices=["basic", "advanced"], help="Type of model to train.")
    parser.add_argument("--force_refetch", action="store_true", help="Force refetching of data even if cached.")
    parser.add_argument("--target_hotel_name", type=str, default=None, help="Specific hotel name to target (e.g., 'Sunset Mirage Villa').")
    parser.add_argument("--force_fetch_delay_hours", type=int, default=None, help="Force refetch data if older than this many hours. Defaults to 24 if target_hotel_name is provided, otherwise 7 days.")

    args = parser.parse_args()

    # Convert force_fetch_delay_hours to timedelta if provided, else use default logic
    force_fetch_delay = None
    if args.force_fetch_delay_hours is not None:
        force_fetch_delay = timedelta(hours=args.force_fetch_delay_hours)
    elif args.target_hotel_name: # Default to 24 hours if target_hotel_name is provided
        force_fetch_delay = timedelta(hours=24)
    else: # Default to 7 days otherwise
        force_fetch_delay = timedelta(days=7)


    print(
        f"Running scrape_booking_com_data for destination='{args.destination}', "
        f"adults={args.adults}, rooms={args.rooms}, limit={args.limit}, "
        f"hotel_details_limit={args.hotel_details_limit}, model_type='{args.model_type}', "
        f"force_refetch={args.force_refetch}, target_hotel_name='{args.target_hotel_name}', "
        f"force_fetch_delay={force_fetch_delay}"
    )
    
    asyncio.run(
        scrape_booking_com_data(
            destination=args.destination,
            adults=args.adults,
            rooms=args.rooms,
            limit=args.limit,
            hotel_details_limit=args.hotel_details_limit,
            model_type=args.model_type,
            force_refetch=args.force_refetch,
            target_hotel_name=args.target_hotel_name,
            force_fetch_delay=force_fetch_delay
        )
    )
    print("scrape_booking_com_data finished.")
