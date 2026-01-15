import asyncio
import os
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
from playwright.async_api import Browser, Page, async_playwright

from app.data_models import HotelDetails, PropertyListing
from app.prediction.model_utils import (
    save_model_metadata,
    should_retrain_model,
)
from app.prediction.training.basic_trainer import train_model
from app.scrapers.booking_com.extractors.properties_extractor import (
    scrape_properties_data,
)
from app.scrapers.booking_com.extractors.specific_property_extractor import (
    scrape_specific_property_data,
)
from app.scrapers.booking_com.navigation import goto_properties_page
from app.scrapers.booking_com.playwright_urls import BookingComUrls
from app.scrapers.booking_com.processing.concurrent_scrapers import (
    scrape_hotel_data_concurrent,
)
from app.scrapers.booking_com.utils import modal_dismisser
from app.utils.cache import cache_url, get_cached_url
from app.utils.constants import (
    get_model_filepath,
    get_scraped_data_filepath,
)
from app.utils.file_io import (
    read_scraped_data_from_csv,
    save_hotel_detail_data_to_csv,
    save_scraped_data_to_csv,
)
from app.utils.logger import logger


async def scrape_general_data(
    browser: Browser,
    destination: str,
    hotel_details_limit: int,
    adults: int,
    rooms: int,
    limit: int,
    force_refetch: bool,
    force_fetch_delay: Optional[timedelta],
    specific_property_to_exclude: Optional[PropertyListing] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    properties_file_path = get_scraped_data_filepath(
        "properties", destination, adults, rooms, limit
    )
    hotel_details_file_path = get_scraped_data_filepath(
        "hotel_details", destination, adults, rooms, hotel_details_limit
    )

    scraped_properties: pd.DataFrame = pd.DataFrame()
    hotel_details_data: pd.DataFrame = pd.DataFrame()

    delay_seconds = (force_fetch_delay or timedelta(days=7)).total_seconds()

    properties_from_cache = False
    if not force_refetch and os.path.exists(properties_file_path):
        if (time.time() - os.path.getmtime(properties_file_path)) < delay_seconds:
            logger.info(
                f"Attempting to use cached general properties data from {properties_file_path}"
            )
            try:
                scraped_properties = read_scraped_data_from_csv(properties_file_path)
                logger.success(
                    f"Successfully loaded {len(scraped_properties)} general properties from cache."
                )
                properties_from_cache = True
            except Exception as e:
                logger.warning(
                    f"Failed to read cached general properties data: {e}. Will attempt to scrape."
                )

    hotel_details_from_cache = False
    if not force_refetch and os.path.exists(hotel_details_file_path):
        if (time.time() - os.path.getmtime(hotel_details_file_path)) < delay_seconds:
            logger.info(
                f"Attempting to use cached general hotel details data from {hotel_details_file_path}"
            )
            try:
                hotel_details_data = read_scraped_data_from_csv(
                    hotel_details_file_path, is_hotel_detail=True
                )
                logger.success(
                    f"Successfully loaded {len(hotel_details_data)} general hotel details from cache."
                )
                hotel_details_from_cache = True
            except Exception as e:
                logger.warning(
                    f"Failed to read cached general hotel details data: {e}. Will attempt to scrape."
                )

    if not properties_from_cache or not hotel_details_from_cache or force_refetch:
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        try:
            if not properties_from_cache or force_refetch:
                cached_url = None
                try:
                    cached_url = get_cached_url(
                        destination=destination, adults=adults, rooms=rooms
                    )
                except Exception as e:
                    logger.error(f"Error checking cache for URL: {e}")

                if cached_url and not force_refetch:
                    logger.info(f"Proceeding with the cached_URL {cached_url}")
                    await page.goto(cached_url, wait_until="networkidle")
                    await modal_dismisser(page)
                    await page.wait_for_selector(
                        '[data-testid="property-card"]', timeout=30_000
                    )
                else:
                    logger.info("Proceeding to get the URL")
                    urls = BookingComUrls()
                    await goto_properties_page(
                        page=page,
                        destination=destination,
                        urls=urls,
                        adults=adults,
                        rooms=rooms,
                    )
                    await page.wait_for_load_state("networkidle", timeout=60_000)
                    await page.wait_for_selector(
                        '[data-testid="property-card"]', timeout=30_000
                    )
                    current_url = page.url
                    try:
                        cache_url(
                            destination=destination,
                            adults=adults,
                            rooms=rooms,
                            url=current_url,
                        )
                    except Exception as e:
                        logger.error(f"Failed to cache URL: {e}")

                general_properties = await scrape_properties_data(page, limit)
                # Exclude the specific property from general scraping data
                if specific_property_to_exclude:
                    general_properties = [
                        p
                        for p in general_properties
                        if not (
                            p.name == specific_property_to_exclude.name
                            or (
                                p.hotel_link
                                and specific_property_to_exclude.hotel_link
                                and p.hotel_link
                                == specific_property_to_exclude.hotel_link
                            )
                        )
                    ]
                scraped_properties = pd.DataFrame(
                    [asdict(p) for p in general_properties]
                )
                try:
                    save_scraped_data_to_csv(
                        scraped_properties, destination, adults, rooms, limit
                    )
                except Exception as e:
                    logger.error(f"Failed to save scraped properties to CSV: {e}")

            if not hotel_details_from_cache or force_refetch:
                if scraped_properties.empty:
                    logger.warning(
                        "No general properties available to scrape hotel details for."
                    )
                else:
                    hotel_urls_to_scrape: list[str] = [
                        link
                        for link in scraped_properties["hotel_link"].dropna().tolist()
                    ]
                    if hotel_details_limit > 0:
                        hotel_urls_to_scrape = hotel_urls_to_scrape[
                            :hotel_details_limit
                        ]

                    logger.info(
                        f"Scraping details for {len(hotel_urls_to_scrape)} general hotels concurrently."
                    )
                    general_hotel_details = await scrape_hotel_data_concurrent(
                        browser, hotel_urls_to_scrape
                    )
                    if specific_property_to_exclude:
                        general_hotel_details = [
                            h
                            for h in general_hotel_details
                            if not (
                                h.name == specific_property_to_exclude.name
                                or (
                                    h.url
                                    and specific_property_to_exclude.hotel_link
                                    and h.url == specific_property_to_exclude.hotel_link
                                )
                            )
                        ]
                    hotel_details_data = pd.DataFrame(
                        [asdict(h) for h in general_hotel_details]
                    )

                if hotel_details_limit == 0:
                    logger.info(
                        "hotel_details_limit is 0, skipping general hotel detail scraping."
                    )
                    hotel_details_data = pd.DataFrame()

                try:
                    save_hotel_detail_data_to_csv(
                        hotel_details_data,
                        destination,
                        adults,
                        rooms,
                        hotel_details_limit,
                    )
                except Exception as e:
                    logger.error(f"Failed to save general hotel details to CSV: {e}")

        finally:
            await page.close()
            await context.close()

    if scraped_properties.empty:
        logger.warning("No general properties retrieved after scraping or from cache.")

    return scraped_properties, hotel_details_data


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
                        force_refetch=True,
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
                save_model_metadata(model_filepath, metadata)
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

async def run():
    destination = "Unawatuna"
    adults = 2
    rooms = 1
    limit = 300  # Corresponds to properties limit
    hotel_details_limit = 100

    logger.info(
        f"Starting scraping for: Destination={destination}, Adults={adults}, Rooms={rooms}, Properties Limit={limit}, Hotel Details Limit={hotel_details_limit}"
    )

    # Call the main scraping function
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            df_properties, df_hotel_details = await scrape_general_data(
                browser=browser,
                destination=destination,
                hotel_details_limit=hotel_details_limit,
                adults=adults,
                rooms=rooms,
                limit=limit,
                force_refetch=True,  # Set to True to force re-scraping
                force_fetch_delay=None,
                specific_property_to_exclude=None,
            )

            logger.info(f"Scraped {len(df_properties)} properties.")
            logger.info(f"Scraped {len(df_hotel_details)} hotel details.")
        finally:
            await browser.close()

    logger.info("Scraping process finished.")


if __name__ == "__main__":
    asyncio.run(run())