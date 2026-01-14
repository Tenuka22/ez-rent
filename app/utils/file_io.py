import os

import pandas as pd

from app.utils.logger import logger


def save_scraped_data_to_csv(
    data: pd.DataFrame, destination: str, adults: int, rooms: int, limit: int
) -> None:
    """
    Saves a list of PropertyListing objects to a CSV file.

    Args:
        data: List of PropertyListing objects.
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.
        limit: The limit used for scraping.
    """
    file_path = f"./scraped/properties/{destination}/{adults}/{rooms}/limit_{limit}.csv"
    logger.info(
        f"Attempting to save scraped data to CSV: {file_path}. "
        f"Destination='{destination}', Adults={adults}, Rooms={rooms}, Limit={limit}"
    )
    try:
        # Define the directory and file path
        dir_name = os.path.dirname(file_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(dir_name):
            logger.debug(f"Creating directory for scraped data: {dir_name}")
            os.makedirs(dir_name)

        data.to_csv(file_path, index=False)
        logger.info(f"Successfully saved {len(data)} scraped properties to {file_path}")
        return
    except Exception as e:
        logger.error(
            f"Error saving scraped data to CSV at {file_path}: {e}", exc_info=True
        )
        raise Exception(f"Error saving scraped data to CSV: {e}")


def save_hotel_detail_data_to_csv(
    data: pd.DataFrame, destination: str, adults: int, rooms: int, limit: int
) -> None:
    """
    Saves a list of HotelDetails objects to a CSV file.

    Args:
        data: List of HotelDetails objects.
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.
        limit: The limit used for scraping.
    """
    file_path = (
        f"./scraped/hotel_details/{destination}/{adults}/{rooms}/limit_{limit}.csv"
    )
    logger.info(
        f"Attempting to save hotel detail data to CSV: {file_path}. "
        f"Destination='{destination}', Adults={adults}, Rooms={rooms}, Limit={limit}"
    )
    try:
        # Define the directory and file path
        dir_name = os.path.dirname(file_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(dir_name):
            logger.debug(f"Creating directory for hotel detail data: {dir_name}")
            os.makedirs(dir_name)

        # Delete existing file before saving to ensure new JSON format is written
        if os.path.exists(file_path):
            logger.debug(
                f"Removing existing hotel detail file: {file_path} before saving new data."
            )
            os.remove(file_path)

        data.to_csv(file_path, index=False)
        logger.info(
            f"Successfully saved {len(data)} hotel detail records to {file_path}"
        )
        return
    except Exception as e:
        logger.error(
            f"Error saving hotel detail data to CSV at {file_path}: {e}", exc_info=True
        )
        raise Exception(f"Error saving hotel detail data to CSV: {e}")


def read_scraped_data_from_csv(
    file_path: str, is_hotel_detail: bool = False
) -> pd.DataFrame:
    """
    Reads scraped data from a CSV file and returns a list of PropertyListing or HotelDetails objects.

    Args:
        file_path: The path to the CSV file.
        is_hotel_detail: If True, reads data as HotelDetails; otherwise, as PropertyListing.

    Returns:
        List[PropertyListing] | List[HotelDetails]: A list of objects.
    """
    logger.info(
        f"Attempting to read scraped data from CSV: {file_path}. "
        f"is_hotel_detail: {is_hotel_detail}"
    )
    try:
        df = pd.read_csv(file_path)
        logger.debug(f"Read {len(df)} rows from {file_path}.")
        df = df.where(pd.notnull(df), None)
        logger.debug("Replaced NaN values with None in DataFrame.")

        return df
    except Exception as e:
        logger.error(
            f"Error reading scraped data from CSV at {file_path}: {e}", exc_info=True
        )
        raise Exception(f"Error reading scraped data from CSV: {e}")
