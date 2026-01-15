import asyncio
from typing import List

from playwright.async_api import Browser

from app.data_models import HotelDetails
from app.utils.logger import logger
from app.scrapers.booking_com.extractors.hotel_details_extractor import scrape_hotel_data


async def scrape_hotel_data_concurrent(
    browser: Browser, urls: List[str], max_concurrent: int = 5
) -> List[HotelDetails]:
    """
    Scrape multiple hotel pages concurrently.

    Args:
        browser: Playwright browser instance.
        urls: List of hotel URLs to scrape.
        max_concurrent: Maximum number of concurrent scraping tasks.

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
