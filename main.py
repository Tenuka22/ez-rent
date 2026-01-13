import asyncio

from returns.result import Failure

from src.scrapers.booking_com.main_scraper import (
    scrape_booking_com_data,
)
from src.utils.logger import logger


async def main():
    """Main function to run the scraper with user-provided values."""
    logger.info("Please provide the scraping parameters:")

    destination = input("Enter destination (e.g., Unawatuna): ")
    while not destination:
        logger.warning("Destination cannot be empty.")
        destination = input("Enter destination (e.g., Unawatuna): ")

    adults_str = input("Enter number of adults (default: 2): ")
    adults = int(adults_str) if adults_str.isdigit() else 2

    rooms_str = input("Enter number of rooms (default: 1): ")
    rooms = int(rooms_str) if rooms_str.isdigit() else 1

    limit_str = input("Enter limit of properties to scrape (default: 100): ")
    limit = int(limit_str) if limit_str.isdigit() else 100

    force_refetch_str = input("Force refetch? (y/N, default: N): ").lower()
    force_refetch = force_refetch_str == "y"

    logger.info("\nStarting scraper with parameters:")
    logger.debug(f"  Destination: {destination}")
    logger.debug(f"  Adults: {adults}")
    logger.debug(f"  Rooms: {rooms}")
    logger.debug(f"  Limit: {limit}")
    logger.debug(f"  Force Refetch: {force_refetch}")
    logger.info("-" * 30)

    data_result = await scrape_booking_com_data(
        destination=destination,
        adults=adults,
        rooms=rooms,
        limit=limit,
        force_refetch=force_refetch,
    )
    if isinstance(data_result, Failure):
        logger.error(f"Scraping failed: {data_result.failure()}")
        return

    data = data_result.unwrap()
    logger.success(f"Scraping successful! Found {len(data)} properties.")


if __name__ == "__main__":
    asyncio.run(main())
