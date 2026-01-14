import asyncio

import pandas as pd

from app.prediction.price_model import (
    train_price_prediction_model_without_high_level_data,
)
from app.scrapers.booking_com.main_scraper import (
    scrape_booking_com_data,
)
from app.utils.logger import logger


async def main():
    """Main function to run the scraper with user-provided values."""
    destination = "Unawatuna"
    adults = 2
    rooms = 1
    limit = 20
    hotel_details_limit = 5
    force_refetch = False
    logger.info("\nStarting scraper with parameters:")
    logger.debug(f"  Destination: {destination}")
    logger.debug(f"  Adults: {adults}")
    logger.debug(f"  Rooms: {rooms}")
    logger.debug(f"  Limit: {limit}")
    logger.debug(f"  Force Refetch: {force_refetch}")
    logger.info("-" * 30)

    try:
        (property_data, property_details_data) = await scrape_booking_com_data(
            destination=destination,
            adults=adults,
            rooms=rooms,
            limit=limit,
            hotel_details_limit=hotel_details_limit,
            force_refetch=force_refetch,
        )
        logger.success(f"Scraping successful! Found {len(property_data)} properties.")

        df = pd.DataFrame(
            property_data
        )  # Convert list of ScrapedData objects to DataFrame

        await train_price_prediction_model_without_high_level_data(
            df,
            destination=destination,
            adults=adults,
            rooms=rooms,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
