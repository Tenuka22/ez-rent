import os
import pandas as pd

from app.utils.constants import URL_CSV_PATH
from app.utils.logger import logger


def cache_url(
    destination: str, adults: int, rooms: int, url: str
) -> None:
    """
    Caches a URL for a given destination, adults, and rooms.

    Args:
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.
        url: The URL to cache.

    Raises:
        Exception: If an error occurs while caching the URL.
    """
    logger.info(
        f"Attempting to cache URL for destination='{destination}', adults={adults}, "
        f"rooms={rooms}: {url}"
    )
    try:
        dir_name = os.path.dirname(URL_CSV_PATH)
        if dir_name and not os.path.exists(dir_name):
            logger.debug(f"Creating directory for URL cache: {dir_name}")
            os.makedirs(dir_name)

        new_row = pd.DataFrame(
            [
                {
                    "destination": destination,
                    "adults": adults,
                    "rooms": rooms,
                    "url": url,
                }
            ]
        )

        if os.path.exists(URL_CSV_PATH):
            df_urls = pd.read_csv(URL_CSV_PATH)
            df_urls = pd.concat([df_urls, new_row], ignore_index=True)
            logger.debug(f"Appending new URL to existing cache file: {URL_CSV_PATH}")
        else:
            df_urls = new_row
            logger.debug(f"Creating new cache file: {URL_CSV_PATH}")

        df_urls.to_csv(URL_CSV_PATH, index=False)
        logger.info(f"Successfully cached URL for {destination}.")
        return None
    except Exception as e:
        logger.error(f"Error caching URL for {destination}: {e}", exc_info=True)
        raise Exception(f"Error caching URL: {e}")
