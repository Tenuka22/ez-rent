import os
import re
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.core_logic import run_prediction_flow
from app.utils.constants import (
    get_all_prediction_files_metadata,  # This might become obsolete
)
from app.utils.file_io.read_scraped_data_from_csv import read_scraped_data_from_csv
from app.utils.logger import logger
from app.utils.scraped_data_loader import (  # New imports
    deduplicate_by_latest,
    get_all_predictions_data,
)
from server.schemas import (
    PaginatedPredictionDataResponse,
    PredictionHistoryEntry,
    PredictionHistoryResponse,
    PredictionResponse,
    ScrapeAndPredictRequest,
)

router = APIRouter()


@router.post(
    "/scrape-and-predict",
    response_model=PredictionResponse,
    summary="Scrape Hotel Data and Predict Price",
)
async def scrape_and_predict(request: ScrapeAndPredictRequest):
    """
    Scrapes data for a specific hotel from Booking.com, then uses a trained model
    to predict its price based on the provided parameters.
    """
    try:
        predicted_df = await run_prediction_flow(
            data_source="scrape",
            destination=request.destination,
            adults=request.adults,
            rooms=request.rooms,
            properties_limit=request.properties_limit,
            hotel_details_limit=request.hotel_details_limit,
            force_refetch=request.force_refetch,
            prediction_model_type=request.prediction_model_type,
            target_hotel_name=request.target_hotel_name,
        )

        if predicted_df is None or predicted_df.empty:
            raise HTTPException(
                status_code=404,
                detail="Could not find the target hotel or no data was available for prediction.",
            )

        return PredictionResponse(
            predicted_prices=predicted_df.to_dict(orient="records"),
            message="Price prediction successful!",
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Prediction model not found. Please ensure the model is trained.",
        )
    except Exception as e:
        logger.error(f"API Error in /scrape-and-predict: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/predictions/history",
    response_model=PredictionHistoryResponse,
    summary="Get List of Previous Prediction Runs",
)
async def get_prediction_history(
    model_type: Optional[str] = Query(
        None, description="Filter by prediction model type (basic or advanced)"
    ),
    # Removed destination, adults, rooms, properties_limit, hotel_details_limit
    skip: int = Query(0, description="Number of items to skip"),
    page_size: int = Query(20, description="Number of items to return per page"),
):
    """
    Retrieves a paginated list of all previously saved prediction results, with optional filters.
    """
    df_all_predictions = get_all_predictions_data()

    if df_all_predictions.empty:
        return PredictionHistoryResponse(
            predictions=[], total=0, skip=skip, page_size=page_size
        )

    # Deduplicate by hotel name and model type, keeping the newest prediction
    # This assumes 'name' in prediction data refers to the hotel name
    df_deduplicated_predictions = deduplicate_by_latest(
        df_all_predictions, key_cols=["name", "model_type"], timestamp_col="timestamp"
    )

    filtered_entries_df = df_deduplicated_predictions
    if model_type:
        filtered_entries_df = filtered_entries_df[
            filtered_entries_df["model_type"] == model_type
        ]

    all_entries = []
    for _, row in filtered_entries_df.iterrows():
        # Ensure 'timestamp' is in string format for PredictionHistoryEntry
        entry_data = row.to_dict()
        if isinstance(entry_data.get("timestamp"), datetime):
            entry_data["timestamp"] = entry_data["timestamp"].strftime("%Y%m%d_%H%M%S")

        # Need to ensure all fields expected by PredictionHistoryEntry are present, or make them optional
        # Based on its definition: model_type, destination, adults, rooms, properties_limit, hotel_details_limit, timestamp, filename, full_path

        entry = PredictionHistoryEntry(
            model_type=entry_data.get("model_type"),
            destination=entry_data.get("destination"),
            adults=entry_data.get("adults"),
            rooms=entry_data.get("rooms"),
            properties_limit=entry_data.get("properties_limit"),
            hotel_details_limit=entry_data.get("hotel_details_limit"),
            timestamp=entry_data.get(
                "timestamp"
            ),  # Now this should be a string from strftime
            filename=entry_data.get("filename"),
            full_path=entry_data.get("full_path"),
        )
        all_entries.append(entry)

    total_entries = len(all_entries)
    paginated_entries = all_entries[skip : skip + page_size]

    return PredictionHistoryResponse(
        predictions=paginated_entries,
        total=total_entries,
        skip=skip,
        page_size=page_size,
    )


@router.get(
    "/predictions/history/fetch",
    response_model=PaginatedPredictionDataResponse,
    summary="Fetch Specific Prediction Data",
)
async def fetch_prediction_data(
    hotel_name: str = Query(
        ..., description="Name of the hotel (villa) to fetch prediction for"
    ),
    model_type: str = Query(
        ..., description="Prediction model type (basic or advanced)"
    ),
    # Removed destination, adults, rooms, properties_limit, hotel_details_limit, timestamp
    skip: int = Query(0, description="Number of items to skip"),
    page_size: int = Query(20, description="Number of items to return per page"),
):
    """
    Fetches the content of the latest prediction for a specific hotel and model type, with pagination.
    """
    df_all_predictions = get_all_predictions_data()

    if df_all_predictions.empty:
        raise HTTPException(status_code=404, detail="No prediction data available.")

    # Filter by model_type and hotel_name
    filtered_by_hotel_and_model = df_all_predictions[
        (df_all_predictions["model_type"] == model_type)
        & (df_all_predictions["name"].str.contains(hotel_name, case=False, na=False))
    ]

    if filtered_by_hotel_and_model.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No prediction found for hotel '{hotel_name}' with model type '{model_type}'.",
        )

    # Get the single latest prediction entry for this hotel and model type
    latest_prediction_entry = deduplicate_by_latest(
        filtered_by_hotel_and_model,
        key_cols=["name", "model_type"],
        timestamp_col="timestamp",
    ).iloc[0]  # Assuming 'name' is the hotel name in prediction CSVs

    # Construct the path to the actual prediction file using metadata
    # The _extract_metadata_from_path already provides 'full_path' and 'filename'
    file_path = latest_prediction_entry["full_path"]

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail=f"Prediction file not found at {file_path}"
        )

    # Load the specific prediction file (which might contain more than one row if it was scraped that way)
    df_predictions_for_file = read_scraped_data_from_csv(file_path)

    # Filter again by hotel_name in case the file contains multiple hotels
    df_predictions_for_file = df_predictions_for_file[
        df_predictions_for_file["name"].str.contains(hotel_name, case=False, na=False)
    ]

    if df_predictions_for_file.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Hotel '{hotel_name}' not found in the latest prediction file.",
        )

    total_data = len(df_predictions_for_file)
    paginated_data = df_predictions_for_file.iloc[skip : skip + page_size]

    return PaginatedPredictionDataResponse(
        data=paginated_data.to_dict(orient="records"),
        total=total_data,
        skip=skip,
        page_size=page_size,
    )
