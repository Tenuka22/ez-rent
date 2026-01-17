import ast
import os
from dataclasses import fields
from typing import List, Any, Dict

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.data_models import HotelDetails, PropertyListing
from app.utils.constants import get_scraped_data_filepath # This might become obsolete
from app.utils.file_io.read_scraped_data_from_csv import read_scraped_data_from_csv
from app.utils.logger import logger
from server.schemas import PropertyDetailsResponse, PaginatedPropertiesResponse
from server.utils import normalize_booking_url
from app.utils.scraped_data_loader import get_all_properties_data, get_all_hotel_details_data, deduplicate_by_latest


router = APIRouter()


@router.get(
    "/properties",
    response_model=PaginatedPropertiesResponse,
    summary="Get All Scraped Properties (Paginated)",
)
async def get_all_properties(
    # Removed destination, adults, rooms, limit as query parameters
    skip: int = Query(0, description="Number of items to skip"),
    page_size: int = Query(20, description="Number of items to return per page"),
):
    """
    Retrieves a paginated list of all scraped properties, keeping only the newest entry for each property.
    """
    df_all_properties = get_all_properties_data()
    
    if df_all_properties.empty:
        return PaginatedPropertiesResponse(properties=[], total=0, skip=skip, page_size=page_size)

    # Deduplicate by property name, keeping the one from the most recently modified file
    df_deduplicated = deduplicate_by_latest(df_all_properties, key_cols=["name"], timestamp_col="file_mtime")

    total_properties = len(df_deduplicated)
    paginated_df = df_deduplicated.iloc[skip : skip + page_size]

    properties = [
        PropertyListing(**row)
        for row in paginated_df.to_dict(orient="records")
    ]

    return PaginatedPropertiesResponse(properties=properties, total=total_properties, skip=skip, page_size=page_size)


@router.get(
    "/properties/details",
    response_model=PropertyDetailsResponse,
    summary="Get Details for a Specific Property",
)
async def get_property_details(
    hotel_name: str = Query(..., description="Name of the hotel to get details for"),
    # Removed destination, adults, rooms, limit, hotel_details_limit as query parameters
):
    """
    Retrieves the scraped details for a single property from the stored CSV files,
    prioritizing the newest available data.
    """
    df_all_properties = get_all_properties_data()
    df_all_details = get_all_hotel_details_data()

    if df_all_properties.empty or df_all_details.empty:
        raise HTTPException(status_code=404, detail="No scraped data available.")

    # Filter properties by hotel name
    property_listing_matches = df_all_properties[
        df_all_properties["name"].str.contains(hotel_name, case=False, na=False)
    ]

    if property_listing_matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Property '{hotel_name}' not found in any scraped properties.",
        )
    
    # Deduplicate property listings by name, keeping the newest one
    # If a property appears in multiple configs, we want the data from the latest scrape run
    latest_property_listing = deduplicate_by_latest(property_listing_matches, key_cols=["name"], timestamp_col="file_mtime")

    if latest_property_listing.empty: # Should not happen if property_listing_matches was not empty
        raise HTTPException(
            status_code=404,
            detail=f"Property '{hotel_name}' not found after deduplication.",
        )

    # Get the single latest property listing
    property_data_row = latest_property_listing.iloc[0]

    property_dict = property_data_row.where(pd.notnull(property_data_row), None).to_dict()
    pl_fields = {f.name for f in fields(PropertyListing)}
    property_listing = PropertyListing(
        **{k: v for k, v in property_dict.items() if k in pl_fields}
    )

    hotel_details = None
    # Now try to find the corresponding hotel details using the metadata from the selected property listing
    # We need to match on destination, adults, rooms, hotel_details_limit inferred from the properties file's path
    # and the hotel_link
    matching_details_config = df_all_details[
        (df_all_details["destination"] == property_data_row["destination"]) &
        (df_all_details["adults"] == property_data_row["adults"]) &
        (df_all_details["rooms"] == property_data_row["rooms"])
        # We cannot match on properties_limit or hotel_details_limit directly as these are from *different* files
        # The crucial part is matching the hotel_link within the selected config
    ]
    
    if not matching_details_config.empty:
        hotel_link = property_listing.hotel_link
        normalized_link = normalize_booking_url(hotel_link)

        # Filter details from the matching config by normalized URL
        hotel_details_data = matching_details_config[matching_details_config["normalized_url"] == normalized_link]

        if not hotel_details_data.empty:
            # Again, if multiple hotel_details files match, take the newest one
            latest_hotel_details_entry = deduplicate_by_latest(hotel_details_data, key_cols=["normalized_url"], timestamp_col="file_mtime").iloc[0]

            details_dict = (
                latest_hotel_details_entry
                .where(pd.notnull(latest_hotel_details_entry), None)
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


@router.get(
    "/properties/compare",
    response_model=List[PropertyDetailsResponse],
    summary="Compare Details for Multiple Properties",
)
async def compare_properties(
    hotel_names: List[str] = Query(..., description="A list of hotel names to compare."),
    # Removed destination, adults, rooms, limit, hotel_details_limit as query parameters
):
    """
    Retrieves and compares the scraped details for multiple properties, prioritizing the newest available data.
    """
    results = []
    for hotel_name in hotel_names:
        try:
            details = await get_property_details(
                hotel_name=hotel_name,
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
