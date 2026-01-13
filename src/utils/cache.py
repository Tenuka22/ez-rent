import os
from typing import Optional

import pandas as pd
from returns.result import Failure, Result, Success # Added imports

URL_CSV_PATH = "./scraped/urls.csv"


def get_cached_url(
    destination: str, adults: int, rooms: int
) -> Result[Optional[str], str]:
    """
    Retrieves a cached URL for a given destination, adults, and rooms.

    Args:
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.

    Returns:
        Result[Optional[str], str]: Success(URL) if found, Success(None) if not found,
                                     or Failure with an error message on exception.
    """
    try:
        if not os.path.exists(URL_CSV_PATH):
            return Success(None)

        df_urls = pd.read_csv(URL_CSV_PATH)
        row = df_urls[
            (df_urls["destination"] == destination)
            & (df_urls["adults"] == adults)
            & (df_urls["rooms"] == rooms)
        ]
        if not row.empty:
            return Success(row.iloc[0]["url"])
        return Success(None)
    except Exception as e:
        return Failure(f"Error getting cached URL: {e}")

def cache_url(
    destination: str, adults: int, rooms: int, url: str
) -> Result[None, str]:
    """
    Caches a URL for a given destination, adults, and rooms.

    Args:
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.
        url: The URL to cache.

    Returns:
        Result[None, str]: Success(None) if caching is successful, Failure with an error message otherwise.
    """
    try:
        if (dir_name := os.path.dirname(URL_CSV_PATH)) and not os.path.exists(dir_name):
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
        else:
            df_urls = new_row

        df_urls.to_csv(URL_CSV_PATH, index=False)
        return Success(None)
    except Exception as e:
        return Failure(f"Error caching URL: {e}")
