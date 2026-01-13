import os
from typing import List

import pandas as pd

from src.core.data_models import ScrapedData

BOOKING_COM_DATA_CSV_PATH = "./scraped/booking_com_data.csv"


def save_scraped_data_to_csv(
    data: List[ScrapedData], destination: str, adults: int, rooms: int
) -> None:
    if not data:
        return

    # Define the directory and file path
    file_path = f"./scraped/properties/{destination}/{adults}/{rooms}/data.csv"
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
        }
        for d in data
    ]

    new_df = pd.DataFrame(data_dicts)
    new_df.to_csv(file_path, index=False)
