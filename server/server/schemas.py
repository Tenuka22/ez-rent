from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.data_models import HotelDetails, PropertyListing


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


class ScrapeConfig(BaseModel):
    destination: str
    adults: int
    rooms: int
    properties_limit: int
    hotel_details_limit: Optional[int] = None


class AvailableScrapesResponse(BaseModel):
    available_scrapes: List[ScrapeConfig]


class PropertyDetailsResponse(BaseModel):
    property_listing: Optional[PropertyListing] = None
    hotel_details: Optional[HotelDetails] = None


class PaginatedPropertiesResponse(BaseModel):
    properties: List[PropertyListing]
    total: int
    skip: int = 0
    page_size: int = 20


class PaginatedScrapesResponse(BaseModel):
    available_scrapes: List[ScrapeConfig]
    total: int
    skip: int = 0
    page_size: int = 20


class PredictionHistoryEntry(BaseModel):
    model_type: str
    destination: str
    adults: int
    rooms: int
    properties_limit: Optional[int]
    hotel_details_limit: Optional[int]
    timestamp: str
    filename: str
    full_path: str

class PredictionHistoryResponse(BaseModel):
    predictions: List[PredictionHistoryEntry]
    total: int
    skip: int = 0
    page_size: int = 20


class PaginatedPredictionDataResponse(BaseModel):
    data: List[dict]
    total: int
    skip: int = 0
    page_size: int = 20