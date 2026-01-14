import asyncio
import os
import re
import time
from typing import List, Optional, cast

import pandas as pd
from playwright.async_api import Browser, async_playwright

from app.data_models import HotelDetails, PropertyListing
from app.scrapers.booking_com.browser import (
    extract_float_value,  # Import extract_float_value
    extract_price_components,  # Import extract_price_components
    modal_dismisser,
    scrape_hotel_data,
    scrape_properties_data,
)
from app.scrapers.booking_com.navigation import goto_properties_page
from app.scrapers.booking_com.playwright_urls import BookingComUrls
from app.utils.cache import cache_url, get_cached_url
from app.utils.file_io import (
    read_scraped_data_from_csv,
    save_hotel_detail_data_to_csv,
    save_scraped_data_to_csv,
)
from app.utils.logger import logger


def extract_star_rating_float(star_rating_str: str | None) -> float | None:
    logger.debug(f"extract_star_rating_float: Input star_rating_str: {star_rating_str}")
    if star_rating_str:
        match = re.search(r"(\d+)-star", star_rating_str)
        if match:
            rating = float(match.group(1))
            logger.debug(f"extract_star_rating_float: Found star rating: {rating}")
            return rating
    logger.debug("extract_star_rating_float: No star rating found or input is None.")
    return None


def extract_guest_rating_float(guest_rating_str: str | None) -> float | None:
    logger.debug(
        f"extract_guest_rating_float: Input guest_rating_str: {guest_rating_str}"
    )
    if guest_rating_str:
        # Assuming guest_rating_str is like "8.5 Excellent" or just "8.5"
        match = re.search(
            r"(\d+(\.\d+)?)", guest_rating_str
        )  # Changed re.re to re.search
        if match:
            rating = float(match.group(1))
            logger.debug(f"extract_guest_rating_float: Found guest rating: {rating}")
            return rating
    logger.debug("extract_guest_rating_float: No guest rating found or input is None.")
    return None


async def scrape_hotel_data_concurrent(
    browser: Browser, urls: List[str], max_concurrent: int = 5
) -> List[HotelDetails]:
    """
    Scrape multiple hotel pages concurrently.

    Args:
        browser: Playwright browser instance
        urls: List of hotel URLs to scrape
        max_concurrent: Maximum number of concurrent scraping tasks

    Returns:
        List[HotelDetails]: A list of HotelDetails objects.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def scrape_with_semaphore(url: str):
        async with semaphore:
            context = await browser.new_context()
            page = await context.new_page()
            try:
                result = await scrape_hotel_data(page, url)
                return result
            finally:
                await page.close()
                await context.close()

    # Create tasks for all URLs
    tasks = [scrape_with_semaphore(url) for url in urls]

    # Execute with progress logging
    logger.info(
        f"Starting concurrent scraping of {len(urls)} hotels with max {max_concurrent} concurrent tasks"
    )
    completed_results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_results = []
    # Process results from concurrent tasks
    for result in completed_results:
        if isinstance(result, Exception):
            logger.error(f"Task failed with exception: {result}")
        else:
            successful_results.append(result)

    logger.info(
        f"Completed scraping {len(successful_results)} out of {len(urls)} hotels"
    )
    return successful_results


async def scrape_booking_com_data(
    destination: str,
    hotel_details_limit: int = 10,
    adults: int = 2,
    rooms: int = 1,
    limit: int = 100,
    force_refetch: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.debug(f"hotel_details_limit received: {hotel_details_limit}")
    properties_file_path = (
        f"./scraped/properties/{destination}/{adults}/{rooms}/limit_{limit}.csv"
    )
    hotel_details_file_path = f"./scraped/hotel_details/{destination}/{adults}/{rooms}/limit_{hotel_details_limit}.csv"

    scraped_properties: pd.DataFrame | None = None
    hotel_details_data: pd.DataFrame | None = None

    properties_from_cache = False
    if not force_refetch and os.path.exists(properties_file_path):
        if (time.time() - os.path.getmtime(properties_file_path)) < 86400:  # 24 hours
            logger.info(
                f"Attempting to use cached properties data from {properties_file_path}"
            )
            try:
                scraped_properties = read_scraped_data_from_csv(properties_file_path)
                logger.success(
                    f"Successfully loaded {len(scraped_properties)} properties from cache."
                )
                properties_from_cache = True
            except Exception as e:
                logger.warning(
                    f"Failed to read cached properties data: {e}. Will attempt to scrape."
                )

    hotel_details_from_cache = False
    if not force_refetch and os.path.exists(hotel_details_file_path):
        if (
            time.time() - os.path.getmtime(hotel_details_file_path)
        ) < 86400:  # 24 hours
            logger.info(
                f"Attempting to use cached hotel details data from {hotel_details_file_path}"
            )
            try:
                hotel_details_data = read_scraped_data_from_csv(
                    hotel_details_file_path, is_hotel_detail=True
                )
                logger.success(
                    f"Successfully loaded {len(hotel_details_data)} hotel details from cache."
                )
                hotel_details_from_cache = True
            except Exception as e:
                logger.warning(
                    f"Failed to read cached hotel details data: {e}. Will attempt to scrape."
                )

    # --- If properties or hotel details are missing, or force_refetch is True, proceed with Playwright ---
    if not properties_from_cache or not hotel_details_from_cache or force_refetch:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, slow_mo=500)
            try:
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()

                # --- Scrape properties if not cached or forced refetch ---
                if not properties_from_cache or force_refetch:
                    cached_url = None
                    try:
                        cached_url = get_cached_url(
                            destination=destination, adults=adults, rooms=rooms
                        )
                    except Exception as e:
                        logger.error(f"Error checking cache for URL: {e}")


                    if (
                        cached_url and not force_refetch
                    ):  # Only use cached URL if not force refetch
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

                        # Save current URL to CSV
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

                    scraped_properties = pd.DataFrame(
                        await scrape_properties_data(page, limit)
                    )
                    try:
                        save_scraped_data_to_csv(
                            scraped_properties, destination, adults, rooms, limit
                        )
                    except Exception as e:
                        logger.error(f"Failed to save scraped properties to CSV: {e}")

                # --- Scrape hotel details if not cached or forced refetch ---
                if not hotel_details_from_cache or force_refetch:
                    if scraped_properties.empty:
                        logger.warning(
                            "No properties available to scrape hotel details for."
                        )
                    else:
                        logger.debug(
                            f"Length of scraped_properties: {len(scraped_properties)}"
                        )
                        hotel_urls_to_scrape: list[str] = [
                            link
                            for link in scraped_properties["hotel_link"].head(hotel_details_limit).dropna().tolist()
                        ]
                        logger.debug(
                            f"Length of hotel_urls_to_scrape: {len(hotel_urls_to_scrape)}"
                        )

                        logger.info(
                            f"Scraping details for {len(hotel_urls_to_scrape)} hotels concurrently."
                        )
                        hotel_details_data = pd.DataFrame(
                            await scrape_hotel_data_concurrent(browser, hotel_urls_to_scrape)
                        )
                        # Rename columns to match price_model expectations
                        if "discounted_price_value" in hotel_details_data.columns:
                            hotel_details_data.rename(
                                columns={"discounted_price_value": "discounted_price"},
                                inplace=True,
                            )
                        if "taxes_and_fees_value" in hotel_details_data.columns:
                            hotel_details_data.rename(
                                columns={"taxes_and_fees_value": "taxes_and_fees"},
                                inplace=True,
                            )
                        # Rename columns to match price_model expectations
                        if "discounted_price_value" in hotel_details_data.columns:
                            hotel_details_data.rename(
                                columns={"discounted_price_value": "discounted_price"},
                                inplace=True,
                            )
                        if "taxes_and_fees_value" in hotel_details_data.columns:
                            hotel_details_data.rename(
                                columns={"taxes_and_fees_value": "taxes_and_fees"},
                                inplace=True,
                            )

                        try:
                            save_hotel_detail_data_to_csv(
                                hotel_details_data,
                                destination,
                                adults,
                                rooms,
                                hotel_details_limit,
                            )
                        except Exception as e:
                            logger.error(f"Failed to save hotel details to CSV: {e}")

            except Exception as e:
                raise Exception(str(e))
            finally:
                await browser.close()

    if scraped_properties.empty:
        raise Exception("Failed to retrive data from booking_com.")

    return (scraped_properties, hotel_details_data)
