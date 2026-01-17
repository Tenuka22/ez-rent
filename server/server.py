from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core_logic import run_prediction_flow
from app.utils.logger import logger

# --- FastAPI App ---

app = FastAPI(
    title="Ez-Rent Price Predictor",
    description="API for scraping rental data and predicting prices.",
    version="1.0.0",
)


# --- Pydantic Schemas for API ---


class ScrapeAndPredictRequest(BaseModel):
    destination: str = Field(
        "Unawatuna", description="Destination for scraping (e.g., city, region)."
    )
    adults: int = Field(2, description="Number of adults for the booking.")
    rooms: int = Field(1, description="Number of rooms for the booking.")
    properties_limit: int = Field(
        300, description="Maximum number of properties to scrape."
    )
    hotel_details_limit: int = Field(
        100, description="Maximum number of hotel details to scrape."
    )
    force_refetch: bool = Field(
        False, description="If set, forces refetching of data even if cached."
    )
    prediction_model_type: Literal["basic", "advanced"] = Field(
        "basic", description="Type of prediction model to use: 'basic' or 'advanced'."
    )
    target_hotel_name: str = Field(
        "Sunset Mirage Villa",
        description="Specific hotel name to target during scraping.",
    )


class PredictionResponse(BaseModel):
    predicted_prices: list
    message: str


# --- API Endpoints ---


@app.post(
    "/scrape-and-predict",
    response_model=PredictionResponse,
    summary="Scrape Hotel Data and Predict Price",
)
async def scrape_and_predict(request: ScrapeAndPredictRequest):
    """
    Scrapes data for a specific hotel from Booking.com, then uses a trained model
    to predict its price based on the provided parameters.

    This endpoint orchestrates two main processes:
    1.  **Scraping**: Fetches property and detail data for the `target_hotel_name`.
        It also scrapes general market data for the specified `destination` to
        ensure the prediction model is up-to-date.
    2.  **Prediction**: Feeds the scraped data of the target hotel into a
        machine learning model to estimate its price.

    Returns the predicted price and other relevant information.
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
