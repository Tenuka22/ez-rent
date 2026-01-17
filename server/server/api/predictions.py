from fastapi import APIRouter, HTTPException

from app.core_logic import run_prediction_flow
from app.utils.logger import logger
from server.schemas import (
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