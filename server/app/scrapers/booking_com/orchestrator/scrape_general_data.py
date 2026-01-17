import os
import time
from dataclasses import asdict
from datetime import timedelta
from typing import Optional, Tuple

import pandas as pd
from playwright.async_api import Browser, Page

from app.data_models import PropertyListing
from app.scrapers.booking_com.extractors.scrape_properties_data import (
    scrape_properties_data,
)
from app.scrapers.booking_com.navigation.goto_properties_page import goto_properties_page
from app.scrapers.booking_com.playwright_urls import BookingComUrls
from app.scrapers.booking_com.processing.concurrent_scrapers import (
    scrape_hotel_data_concurrent,
)
from app.scrapers.booking_com.utils import modal_dismisser,ensure_usd_and_english_uk
from app.utils.cache.cache_url import cache_url
from app.utils.cache.get_cached_url import get_cached_url
from app.utils.constants import (
    get_scraped_data_filepath,
)
from app.utils.file_io.read_scraped_data_from_csv import read_scraped_data_from_csv
from app.utils.file_io.save_hotel_detail_data_to_csv import save_hotel_detail_data_to_csv
from app.utils.file_io.save_scraped_data_to_csv import save_scraped_data_to_csv
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
        
                    await ensure_usd_and_english_uk(page)

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
