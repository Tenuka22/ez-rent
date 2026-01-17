import os
import re
from typing import List

from fastapi import APIRouter, Query
from app.utils.logger import logger
from server.schemas import ScrapeConfig, PaginatedScrapesResponse

router = APIRouter()


@router.get(
    "/scrapes/available",
    response_model=PaginatedScrapesResponse,
    summary="Get All Available Scraped Data Configurations",
)
async def get_available_scrapes(
    skip: int = Query(0, description="Number of items to skip"),
    page_size: int = Query(20, description="Number of items to return per page"),
):
    """
    Scans the filesystem for scraped data and returns a paginated list of available configurations.
    """
    available_scrapes = []
    base_path = os.path.join("scraped", "properties")
    if not os.path.isdir(base_path):
        return PaginatedScrapesResponse(available_scrapes=[], total=0, skip=skip, page_size=page_size)

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
    
    total_scrapes = len(available_scrapes)
    paginated_scrapes = available_scrapes[skip : skip + page_size]

    return PaginatedScrapesResponse(
        available_scrapes=paginated_scrapes,
        total=total_scrapes,
        skip=skip,
        page_size=page_size
    )