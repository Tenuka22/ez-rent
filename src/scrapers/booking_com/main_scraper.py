import asyncio
import os
import time
from typing import List

from playwright.async_api import Browser, async_playwright
from returns.result import Failure, Result, Success

from src.core.data_models import HotelDetailData, ScrapedData
from src.scrapers.booking_com.browser import (
    modal_dismisser,
    scrape_hotel_data,
    scrape_properties_data,
)
from src.scrapers.booking_com.navigation import goto_properties_page
from src.scrapers.booking_com.playwright_urls import BookingComUrls
from src.utils.cache import cache_url, get_cached_url
from src.utils.file_io import (
    read_scraped_data_from_csv,
    save_hotel_detail_data_to_csv,
    save_scraped_data_to_csv,
)
from src.utils.logger import logger


async def scrape_hotel_data_concurrent(
    browser: Browser, urls: List[str], max_concurrent: int = 5
) -> Result[List[HotelDetailData], str]:
    """
    Scrape multiple hotel pages concurrently.

    Args:
        browser: Playwright browser instance
        urls: List of hotel URLs to scrape
        max_concurrent: Maximum number of concurrent scraping tasks

    Returns:
        Result[List[HotelDetailData], str]: A Success containing a list of HotelDetailData objects or a Failure with an error message.
    """
    results = []
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
        if isinstance(result, Success):
            successful_results.append(result.unwrap())
        elif isinstance(result, Failure):
            logger.error(f"Task failed with error: {result.failure()}")
        elif isinstance(result, Exception):
            logger.error(f"Task failed with unexpected exception: {result}")

    logger.info(
        f"Completed scraping {len(successful_results)} out of {len(urls)} hotels"
    )
    return Success(successful_results)


async def scrape_booking_com_data(
    destination: str,
    adults: int = 2,
    rooms: int = 1,
    limit: int = 40,
    hotel_details_limit: int = 5,
    force_refetch: bool = False,
) -> Result[List[ScrapedData], str]:
    properties_file_path = (
        f"./scraped/properties/{destination}/{adults}/{rooms}/limit_{limit}.csv"
    )

    # Cache check for properties data
    if not force_refetch and os.path.exists(properties_file_path):
        if (time.time() - os.path.getmtime(properties_file_path)) < 86400:  # 24 hours
            logger.info(f"Using cached properties data from {properties_file_path}")
            read_result = read_scraped_data_from_csv(properties_file_path)
            if isinstance(read_result, Failure):
                return Failure(
                    f"Error reading cached data: {read_result.failure()}"
                )
            return read_result

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            cached_url_result = get_cached_url(
                destination=destination, adults=adults, rooms=rooms
            )

            if isinstance(cached_url_result, Failure):
                return Failure(f"Error checking cache: {cached_url_result.failure()}")

            cached_url = cached_url_result.unwrap()
            if cached_url:
                logger.info(f"Proceeding with the cached_URL {cached_url}")
                await page.goto(cached_url, wait_until="networkidle")

                dismiss_result = await modal_dismisser(page)
                if isinstance(dismiss_result, Failure):
                    return Failure(
                        f"Failed to dismiss modal in cached URL flow: {dismiss_result.failure()}"
                    )

                await page.wait_for_selector(
                    '[data-testid="property-card"]', timeout=30_000
                )
            else:
                logger.info("Proceeding to get the URL")
                urls = BookingComUrls()
                result = await goto_properties_page(
                    page=page,
                    destination=destination,
                    urls=urls,
                    adults=adults,
                    rooms=rooms,
                )

                if isinstance(result, Failure):
                    return (
                        result  # Failure is returned, browser will be closed in finally
                    )

                await page.wait_for_load_state("networkidle", timeout=60_000)
                await page.wait_for_selector(
                    '[data-testid="property-card"]', timeout=30_000
                )

                # Save current URL to CSV
                current_url = page.url
                cache_result = cache_url(
                    destination=destination,
                    adults=adults,
                    rooms=rooms,
                    url=current_url,
                )
                if isinstance(cache_result, Failure):
                    logger.error(f"Failed to cache URL: {cache_result.failure()}")

            scraped_data_result = await scrape_properties_data(page, limit)

            if isinstance(scraped_data_result, Success):
                scraped_properties = scraped_data_result.unwrap()
                save_properties_result = save_scraped_data_to_csv(
                    scraped_properties, destination, adults, rooms, limit
                )
                if isinstance(save_properties_result, Failure):
                    logger.error(
                        f"Failed to save scraped properties to CSV: {save_properties_result.failure()}"
                    )

                # Scrape hotel details concurrently for a limited number of top hotels
                hotel_urls_to_scrape: list[str] = [
                    prop.hotel_link
                    for prop in scraped_properties[:hotel_details_limit]
                    if prop.hotel_link is not None
                ]

                logger.info(
                    f"Scraping details for {len(hotel_urls_to_scrape)} hotels concurrently."
                )
                hotel_details_result = await scrape_hotel_data_concurrent(
                    browser, hotel_urls_to_scrape
                )

                if isinstance(hotel_details_result, Success):
                    hotel_details_data = hotel_details_result.unwrap()
                save_hotel_details_result = save_hotel_detail_data_to_csv(
                    hotel_details_data, destination, adults, rooms, hotel_details_limit
                )
                if isinstance(save_hotel_details_result, Failure):
                    logger.error(
                        f"Failed to save hotel details to CSV: {save_hotel_details_result.failure()}"
                    )
                else:
                    logger.error(
                        f"Failed to scrape hotel details: {hotel_details_result.failure()}"
                    )

            return scraped_data_result

        except Exception as e:
            return Failure(str(e))
        finally:
            await browser.close()
