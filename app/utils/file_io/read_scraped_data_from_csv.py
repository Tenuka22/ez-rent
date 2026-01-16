import pandas as pd

from app.utils.logger import logger


def read_scraped_data_from_csv(
    file_path: str, is_hotel_detail: bool = False
) -> pd.DataFrame:
    """
    Reads scraped data from a CSV file into a pandas DataFrame.

    Args:
        file_path (str): The path to the CSV file.
        is_hotel_detail (bool): Flag indicating if the data is hotel detail data.
                                 (Currently not used for different parsing logic, but kept for context).

    Returns:
        pd.DataFrame: The DataFrame containing the scraped data.
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
