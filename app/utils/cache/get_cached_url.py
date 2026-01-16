import os
from typing import Optional

import pandas as pd

from app.utils.constants import URL_CSV_PATH
from app.utils.logger import logger


def get_cached_url(
    destination: str, adults: int, rooms: int
) -> Optional[str]:
    """
    Retrieves a cached URL for a given destination, adults, and rooms.

    Args:
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.

    Returns:
        Optional[str]: URL if found, None if not found.

    Raises:
        Exception: If an error occurs while getting the cached URL.
    """
    logger.info(
        f"Attempting to retrieve cached URL for destination='{destination}', "
        f"adults={adults}, rooms={rooms}."
    )
    try:
        if not os.path.exists(URL_CSV_PATH):
            logger.debug(f"Cache file not found at {URL_CSV_PATH}.")
            return None

        df_urls = pd.read_csv(URL_CSV_PATH)
        row = df_urls[
            (df_urls["destination"] == destination)
            & (df_urls["adults"] == adults)
            & (df_urls["rooms"] == rooms)
        ]
        if not row.empty:
            cached_url = row.iloc[0]["url"]
            logger.info(f"Cached URL found: {cached_url}")
            return cached_url
        logger.debug("No matching cached URL found.")
        return None
    except Exception as e:
        logger.error(f"Error getting cached URL for {destination}: {e}", exc_info=True)
        raise Exception(f"Error getting cached URL: {e}")
