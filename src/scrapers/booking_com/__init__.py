import os
import time
from typing import List

from playwright.async_api import async_playwright
from returns.result import Failure, Result, Success

from src.core.data_models import ScrapedData
from src.scrapers.booking_com.navigation import goto_properties_page
from src.scrapers.booking_com.browser import (
    modal_dismisser,
    scrape_properties_data,
)
from src.scrapers.booking_com.playwright_urls import BookingComUrls
from src.utils.cache import cache_url, get_cached_url
from src.utils.file_io import read_scraped_data_from_csv, save_scraped_data_to_csv
from src.utils.logger import logger


async def scrape_booking_com_data(
    destination: str,
    adults: int = 2,
    rooms: int = 1,
    limit: int = 100,
    force_refetch: bool = False,
) -> Result[List[ScrapedData], str]:
    file_path = f"./scraped/properties/{destination}/{adults}/{rooms}/limit_{limit}.csv"
    if not force_refetch and os.path.exists(file_path):
        if (time.time() - os.path.getmtime(file_path)) < 86400:  # 24 hours
            logger.info(f"Using cached data from {file_path}")
            return Success(read_scraped_data_from_csv(file_path))

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

            cached_url = get_cached_url(
                destination=destination, adults=adults, rooms=rooms
            )

            if cached_url:
                logger.info(f"Proceeding with the cached_URL {cached_url}")
                await page.goto(cached_url, wait_until="networkidle")

                await modal_dismisser(page)

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
                cache_url(
                    destination=destination,
                    adults=adults,
                    rooms=rooms,
                    url=current_url,
                )

            scraped_data_result = await scrape_properties_data(page, limit)

            if isinstance(scraped_data_result, Success):
                save_scraped_data_to_csv(
                    scraped_data_result.unwrap(), destination, adults, rooms, limit
                )

            return scraped_data_result

        except Exception as e:
            return Failure(str(e))
        finally:
            await browser.close()
