import ast
import os
from dataclasses import fields
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.data_models import HotelDetails, PropertyListing
from app.utils.constants import get_scraped_data_filepath
from app.utils.file_io.read_scraped_data_from_csv import read_scraped_data_from_csv
from app.utils.logger import logger
from server.schemas import PropertyDetailsResponse, PaginatedPropertiesResponse
from server.utils import normalize_booking_url

router = APIRouter()


@router.get(
    "/properties",
    response_model=PaginatedPropertiesResponse,
    summary="Get All Scraped Properties (Paginated)",
)
async def get_all_properties(
    destination: str,
    adults: int = 2,
    rooms: int = 1,
    limit: int = 300,
    skip: int = 0,
    page_size: int = 20,
):
    """
    Retrieves a paginated list of all scraped properties for a given configuration.
    """
    properties_path = get_scraped_data_filepath(
        "properties", destination, adults, rooms, limit
    )
    if not os.path.exists(properties_path):
        raise HTTPException(
            status_code=404, detail="Scraped properties data not found."
        )

    df_properties = read_scraped_data_from_csv(properties_path)
    
    total_properties = len(df_properties)
    paginated_df = df_properties.iloc[skip : skip + page_size]

    properties = [
        PropertyListing(**row)
        for row in paginated_df.to_dict(orient="records")
    ]

    return PaginatedPropertiesResponse(properties=properties, total=total_properties)


@router.get(
    "/properties/details",
    response_model=PropertyDetailsResponse,
    summary="Get Details for a Specific Property",
)
async def get_property_details(
    hotel_name: str,
    destination: str,
    adults: int = 2,
    rooms: int = 1,
    limit: int = 300,
    hotel_details_limit: int = 100,
):
    """
    Retrieves the scraped details for a single property from the stored CSV files.
    """
    try:
        properties_path = get_scraped_data_filepath(
            "properties", destination, adults, rooms, limit
        )
        details_path = get_scraped_data_filepath(
            "hotel_details", destination, adults, rooms, hotel_details_limit
        )

        if not os.path.exists(properties_path):
            raise HTTPException(
                status_code=404,
                detail=f"Scraped properties data not found for the given parameters at {properties_path}.",
            )

        df_properties = read_scraped_data_from_csv(properties_path)
        
        property_listing_data = df_properties[
            df_properties["name"].str.contains(hotel_name, case=False, na=False)
        ]

        if property_listing_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Property '{hotel_name}' not found in scraped properties.",
            )

        property_dict = (
            property_listing_data.iloc[0]
            .where(pd.notnull(property_listing_data.iloc[0]), None)
            .to_dict()
        )
        pl_fields = {f.name for f in fields(PropertyListing)}
        property_listing = PropertyListing(
            **{k: v for k, v in property_dict.items() if k in pl_fields}
        )
        
        hotel_details = None
        if os.path.exists(details_path):
            df_details = read_scraped_data_from_csv(details_path, is_hotel_detail=True)
            hotel_link = property_listing_data.iloc[0]["hotel_link"]
            normalized_link = normalize_booking_url(hotel_link)

            df_details["normalized_url"] = df_details["url"].apply(normalize_booking_url)
            hotel_details_data = df_details[df_details["normalized_url"] == normalized_link]

            if not hotel_details_data.empty:
                details_dict = (
                    hotel_details_data.iloc[0]
                    .where(pd.notnull(hotel_details_data.iloc[0]), None)
                    .to_dict()
                )
                list_like_cols = [
                    "most_popular_facilities", "bathroom_facilities", "view_type",
                    "outdoor_facilities", "kitchen_facilities", "room_amenities",
                    "activities", "food_drink", "services", "safety_security",
                    "general_facilities", "spa_wellness", "languages_spoken",
                    "property_highlights",
                ]
                for col in list_like_cols:
                    if col in details_dict and isinstance(details_dict[col], str):
                        try:
                            details_dict[col] = ast.literal_eval(details_dict[col])
                        except (ValueError, SyntaxError):
                            details_dict[col] = [details_dict[col]] if details_dict[col] else []
                hd_fields = {f.name for f in fields(HotelDetails)}
                hotel_details = HotelDetails(
                    **{k: v for k, v in details_dict.items() if k in hd_fields}
                )

        return PropertyDetailsResponse(
            property_listing=property_listing,
            hotel_details=hotel_details,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="One or more data files not found.")
    except Exception as e:
        logger.error(f"API Error in /properties/details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/properties/compare",
    response_model=List[PropertyDetailsResponse],
    summary="Compare Details for Multiple Properties",
)
async def compare_properties(
    hotel_names: List[str] = Query(..., description="A list of hotel names to compare."),
    destination: str = "Unawatuna",
    adults: int = 2,
    rooms: int = 1,
    limit: int = 300,
    hotel_details_limit: int = 100,
):
    """
    Retrieves and compares the scraped details for multiple properties.
    """
    results = []
    for hotel_name in hotel_names:
        try:
            details = await get_property_details(
                hotel_name=hotel_name,
                destination=destination,
                adults=adults,
                rooms=rooms,
                limit=limit,
                hotel_details_limit=hotel_details_limit,
            )
            results.append(details)
        except HTTPException as e:
            if e.status_code == 404:
                # Append a null-containing response to indicate failure for this hotel
                results.append(PropertyDetailsResponse(property_listing=None, hotel_details=None))
                logger.warning(
                    f"Could not find details for hotel '{hotel_name}': {e.detail}"
                )
            else:
                raise e
    return results