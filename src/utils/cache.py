import os
from typing import Optional

import pandas as pd

URL_CSV_PATH = "./scraped/urls.csv"


def get_cached_url(destination: str, adults: int, rooms: int) -> Optional[str]:
    if not os.path.exists(URL_CSV_PATH):
        return None

    df_urls = pd.read_csv(URL_CSV_PATH)
    row = df_urls[
        (df_urls["destination"] == destination)
        & (df_urls["adults"] == adults)
        & (df_urls["rooms"] == rooms)
    ]
    if not row.empty:
        return row.iloc[0]["url"]
    return None


def cache_url(destination: str, adults: int, rooms: int, url: str) -> None:
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
