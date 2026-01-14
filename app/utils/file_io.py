import ast
import json
import os
from dataclasses import asdict
from typing import List

import pandas as pd

from app.data_models import HotelDetails, PropertyListing
from app.utils.logger import logger


def save_scraped_data_to_csv(
    data: List[PropertyListing], destination: str, adults: int, rooms: int, limit: int
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
        if not data:
            logger.debug("No scraped data provided to save. Skipping CSV creation.")
            return

        # Define the directory and file path
        dir_name = os.path.dirname(file_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(dir_name):
            logger.debug(f"Creating directory for scraped data: {dir_name}")
            os.makedirs(dir_name)

        # Convert PropertyListing objects to dictionaries
        data_dicts = [
            {
                "name": d.name,
                "link": d.link,
                "address": d.address,
                "star_rating": d.star_rating,
                "guest_rating_score": d.guest_rating_score,
                "reviews": d.reviews,
                "distance_from_downtown": d.distance_from_downtown,
                "distance_from_beach": d.distance_from_beach,
                "preferred_badge": d.preferred_badge,
                "deal_badge": d.deal_badge,
                "room_type": d.room_type,
                "bed_details": d.bed_details,
                "cancellation_policy": d.cancellation_policy,
                "prepayment_policy": d.prepayment_policy,
                "availability_message": d.availability_message,
                "stay_dates": d.stay_dates,
                "nights_and_guests": d.nights_and_guests,
                "original_price": d.original_price,
                "discounted_price": d.discounted_price,
                "taxes_and_fees": d.taxes_and_fees,
                "hotel_link": d.hotel_link,
            }
            for d in data
        ]

        new_df = pd.DataFrame(data_dicts)
        new_df.to_csv(file_path, index=False)
        logger.info(f"Successfully saved {len(data)} scraped properties to {file_path}")
        return
    except Exception as e:
        logger.error(
            f"Error saving scraped data to CSV at {file_path}: {e}", exc_info=True
        )
        raise Exception(f"Error saving scraped data to CSV: {e}")


def save_hotel_detail_data_to_csv(
    data: List[HotelDetails], destination: str, adults: int, rooms: int, limit: int
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
        if not data:
            logger.debug(
                "No hotel detail data provided to save. Skipping CSV creation."
            )
            return

        # Define the directory and file path
        dir_name = os.path.dirname(file_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(dir_name):
            logger.debug(f"Creating directory for hotel detail data: {dir_name}")
            os.makedirs(dir_name)

        # Convert HotelDetails objects to dictionaries and serialize complex types
        data_dicts = []
        logger.debug("Serializing complex data types for HotelDetails objects.")
        for d in data:
            d_dict = asdict(d)
            if d_dict.get("coordinates") is not None:
                d_dict["coordinates"] = json.dumps(d_dict["coordinates"])
            if d_dict.get("pool_info") is not None:
                d_dict["pool_info"] = json.dumps(d_dict["pool_info"])
            # Serialize list-like strings for facilities
            for key in [
                "most_popular_facilities",
                "bathroom_facilities",
                "view_type",
                "outdoor_facilities",
                "kitchen_facilities",
                "room_amenities",
                "activities",
                "food_drink",
                "internet_info",
                "parking_info",
                "services",
                "safety_security",
                "general_facilities",
                "spa_wellness",
                "languages_spoken",
                "room_types",
                "property_highlights",
            ]:
                if d_dict.get(key) is not None:
                    d_dict[key] = json.dumps(d_dict[key])
            data_dicts.append(d_dict)

        new_df = pd.DataFrame(data_dicts)

        # Delete existing file before saving to ensure new JSON format is written
        if os.path.exists(file_path):
            logger.debug(
                f"Removing existing hotel detail file: {file_path} before saving new data."
            )
            os.remove(file_path)

        new_df.to_csv(file_path, index=False)
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
) -> List[PropertyListing] | List[HotelDetails]:
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

        data = []
        for index, row in df.iterrows():
            if is_hotel_detail:
                row_dict = row.to_dict()
                logger.debug(
                    f"Processing HotelDetails row {index} for deserialization."
                )
                # Deserialize 'coordinates'
                if (
                    row_dict.get("coordinates") is not None
                    and isinstance(row_dict["coordinates"], str)
                    and row_dict["coordinates"] != "None"
                ):
                    try:
                        row_dict["coordinates"] = json.loads(row_dict["coordinates"])
                        logger.debug(f"Deserialized coordinates for row {index}.")
                    except json.JSONDecodeError:
                        try:
                            row_dict["coordinates"] = ast.literal_eval(
                                row_dict["coordinates"]
                            )
                            logger.debug(
                                f"Deserialized coordinates with ast.literal_eval for row {index}."
                            )
                        except (ValueError, SyntaxError):
                            logger.warning(
                                f"Could not deserialize coordinates for row {index}: {row_dict['coordinates']}"
                            )
                            row_dict["coordinates"] = None
                else:
                    row_dict["coordinates"] = None

                # Deserialize 'pool_info'
                if (
                    row_dict.get("pool_info") is not None
                    and isinstance(row_dict["pool_info"], str)
                    and row_dict["pool_info"] != "None"
                ):
                    try:
                        row_dict["pool_info"] = json.loads(row_dict["pool_info"])
                        logger.debug(f"Deserialized pool_info for row {index}.")
                    except json.JSONDecodeError:
                        try:
                            row_dict["pool_info"] = ast.literal_eval(
                                row_dict["pool_info"]
                            )
                            logger.debug(
                                f"Deserialized pool_info with ast.literal_eval for row {index}."
                            )
                        except (ValueError, SyntaxError):
                            logger.warning(
                                f"Could not deserialize pool_info for row {index}: {row_dict['pool_info']}"
                            )
                            row_dict["pool_info"] = None
                else:
                    row_dict["pool_info"] = None

                # Deserialize list-like strings for facilities
                for key in [
                    "most_popular_facilities",
                    "bathroom_facilities",
                    "view_type",
                    "outdoor_facilities",
                    "kitchen_facilities",
                    "room_amenities",
                    "activities",
                    "food_drink",
                    "internet_info",
                    "parking_info",
                    "services",
                    "safety_security",
                    "general_facilities",
                    "spa_wellness",
                    "languages_spoken",
                    "room_types",
                    "property_highlights",
                ]:
                    if (
                        row_dict.get(key) is not None
                        and isinstance(row_dict[key], str)
                        and row_dict[key] != "None"
                    ):
                        try:
                            row_dict[key] = json.loads(row_dict[key])
                            logger.debug(f"Deserialized '{key}' for row {index}.")
                        except json.JSONDecodeError:
                            try:
                                row_dict[key] = ast.literal_eval(row_dict[key])
                                logger.debug(
                                    f"Deserialized '{key}' with ast.literal_eval for row {index}."
                                )
                            except (ValueError, SyntaxError):
                                logger.warning(
                                    f"Could not deserialize '{key}' for row {index}: {row_dict[key]}"
                                )
                                row_dict[key] = None
                    else:
                        row_dict[key] = None
                data.append(HotelDetails(**row_dict))
            else:
                data.append(PropertyListing(**row.to_dict()))
        logger.info(
            f"Successfully read {len(data)} records as {'HotelDetails' if is_hotel_detail else 'PropertyListing'} from {file_path}."
        )
        return data
    except Exception as e:
        logger.error(
            f"Error reading scraped data from CSV at {file_path}: {e}", exc_info=True
        )
        raise Exception(f"Error reading scraped data from CSV: {e}")
