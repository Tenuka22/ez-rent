import os
import re
from typing import List

from fastapi import APIRouter
from app.utils.logger import logger
from server.schemas import ScrapeConfig, AvailableScrapesResponse

router = APIRouter()


@router.get(
    "/scrapes/available",
    response_model=AvailableScrapesResponse,
    summary="Get All Available Scraped Data Configurations",
)
async def get_available_scrapes():
    """
    Scans the filesystem for scraped data and returns a list of available configurations.
    """
    available_scrapes = []
    base_path = os.path.join("scraped", "properties")
    if not os.path.isdir(base_path):
        return AvailableScrapesResponse(available_scrapes=[])

    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".csv"):
                match = re.match(r"limit_(\d+)\.csv", file)
                if not match:
                    continue
                
                properties_limit = int(match.group(1))
                
                parts = root.replace(base_path, "").strip(os.sep).split(os.sep)
                if len(parts) == 3:
                    destination, adults, rooms = parts
                    try:
                        adults = int(adults)
                        rooms = int(rooms)
                    except ValueError:
                        continue

                    # Check for corresponding hotel_details
                    hotel_details_path_base = os.path.join("scraped", "hotel_details", destination, str(adults), str(rooms))
                    hotel_details_limit = None
                    if os.path.isdir(hotel_details_path_base):
                        for details_file in os.listdir(hotel_details_path_base):
                            details_match = re.match(r"limit_(\d+)\.csv", details_file)
                            if details_match:
                                hotel_details_limit = int(details_match.group(1))
                                break
                    
                    config = ScrapeConfig(
                        destination=destination,
                        adults=adults,
                        rooms=rooms,
                        properties_limit=properties_limit,
                        hotel_details_limit=hotel_details_limit
                    )
                    available_scrapes.append(config)

    return AvailableScrapesResponse(available_scrapes=available_scrapes)