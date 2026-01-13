import os
from dataclasses import asdict  # Added asdict
from typing import List

import pandas as pd
from returns.result import Failure, Result, Success # Added imports

from src.core.data_models import HotelDetailData, ScrapedData


def save_scraped_data_to_csv(
    data: List[ScrapedData], destination: str, adults: int, rooms: int, limit: int
) -> Result[None, str]:
    """
    Saves a list of ScrapedData objects to a CSV file.

    Args:
        data: List of ScrapedData objects.
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.
        limit: The limit used for scraping.

    Returns:
        Result[None, str]: Success(None) if saving is successful, Failure with an error message otherwise.
    """
    try:
        if not data:
            return Success(None)

        # Define the directory and file path
        file_path = f"./scraped/properties/{destination}/{adults}/{rooms}/limit_{limit}.csv"
        dir_name = os.path.dirname(file_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        # Convert ScrapedData objects to dictionaries
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
                "hotel_link": d.hotel_link,  # Added hotel_link
            }
            for d in data
        ]

        new_df = pd.DataFrame(data_dicts)
        new_df.to_csv(file_path, index=False)
        return Success(None)
    except Exception as e:
        return Failure(f"Error saving scraped data to CSV: {e}")

def save_hotel_detail_data_to_csv(
    data: List[HotelDetailData], destination: str, adults: int, rooms: int, limit: int
) -> Result[None, str]:
    """
    Saves a list of HotelDetailData objects to a CSV file.

    Args:
        data: List of HotelDetailData objects.
        destination: The destination string.
        adults: The number of adults.
        rooms: The number of rooms.
        limit: The limit used for scraping.

    Returns:
        Result[None, str]: Success(None) if saving is successful, Failure with an error message otherwise.
    """
    try:
        if not data:
            return Success(None)

        # Define the directory and file path
        file_path = (
            f"./scraped/hotel_details/{destination}/{adults}/{rooms}/limit_{limit}.csv"
        )
        dir_name = os.path.dirname(file_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        # Convert HotelDetailData objects to dictionaries
        data_dicts = [asdict(d) for d in data]

        new_df = pd.DataFrame(data_dicts)
        new_df.to_csv(file_path, index=False)
        return Success(None)
    except Exception as e:
        return Failure(f"Error saving hotel detail data to CSV: {e}")

def read_scraped_data_from_csv(file_path: str) -> Result[List[ScrapedData], str]:
    """
    Reads scraped data from a CSV file and returns a list of ScrapedData objects.

    Args:
        file_path: The path to the CSV file.

    Returns:
        Result[List[ScrapedData], str]: Success containing a list of ScrapedData objects,
                                         or Failure with an error message on exception.
    """
    try:
        df = pd.read_csv(file_path)
        # Replace NaN with None for proper ScrapedData initialization
        df = df.where(pd.notnull(df), None)

        data = []
        for _, row in df.iterrows():
            data.append(ScrapedData(**row.to_dict()))
        return Success(data)
    except Exception as e:
        return Failure(f"Error reading scraped data from CSV: {e}")
