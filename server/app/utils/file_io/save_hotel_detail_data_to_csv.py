import os

import pandas as pd

from app.utils.constants import HOTEL_DETAILS_CSV_PATH_TEMPLATE
from app.utils.logger import logger


def save_hotel_detail_data_to_csv(
    data: pd.DataFrame, destination: str, adults: int, rooms: int, limit: int
) -> None:
    """
    Saves hotel detail data to a CSV file.

    Args:
        data (pd.DataFrame): The DataFrame containing the hotel detail data.
        destination (str): The destination string, used for constructing the file path.
        adults (int): The number of adults, used for constructing the file path.
        rooms (int): The number of rooms, used for constructing the file path.
        limit (int): The scraping limit, used for constructing the file path.
    """
    file_path = HOTEL_DETAILS_CSV_PATH_TEMPLATE.format(
        destination=destination, adults=adults, rooms=rooms, limit=limit
    )
    logger.info(
        f"Attempting to save hotel detail data to CSV: {file_path}. "
        f"Destination='{destination}', Adults={adults}, Rooms={rooms}, Limit={limit}"
    )
    try:
        dir_name = os.path.dirname(file_path)
        if not os.path.exists(dir_name):
            logger.debug(f"Creating directory for hotel detail data: {dir_name}")
            os.makedirs(dir_name)

        if os.path.exists(file_path):
            logger.debug(
                f"Removing existing hotel detail file: {file_path} before saving new data."
            )
            os.remove(file_path)

        data.to_csv(file_path, index=False)
        logger.info(
            f"Successfully saved {len(data)} hotel detail records to {file_path}"
        )
    except Exception as e:
        logger.error(
            f"Error saving hotel detail data to CSV at {file_path}: {e}", exc_info=True
        )
        raise Exception(f"Error saving hotel detail data to CSV: {e}")
