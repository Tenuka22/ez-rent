# app/utils/constants.py

# Templates for scraped data CSV file paths
PROPERTIES_CSV_PATH_TEMPLATE = (
    "./scraped/properties/{destination}/{adults}/{rooms}/limit_{limit}.csv"
)
HOTEL_DETAILS_CSV_PATH_TEMPLATE = (
    "./scraped/hotel_details/{destination}/{adults}/{rooms}/limit_{limit}.csv"
)

# Directory for storing machine learning model artifacts
ML_MODEL_DIR = "./ml_files"


def get_scraped_data_filepath(
    data_type: str, destination: str, adults: int, rooms: int, limit: int
) -> str:
    """
    Constructs the correct file path for scraped data CSVs.
    data_type can be "properties" or "hotel_details".
    """
    if data_type == "properties":
        return PROPERTIES_CSV_PATH_TEMPLATE.format(
            destination=destination, adults=adults, rooms=rooms, limit=limit
        )
    elif data_type == "hotel_details":
        return HOTEL_DETAILS_CSV_PATH_TEMPLATE.format(
            destination=destination, adults=adults, rooms=rooms, limit=limit
        )
    else:
        raise ValueError(f"Unknown data_type: {data_type}")


def get_model_filepath(
    destination: str,
    adults: int,
    rooms: int,
    properties_limit: int,
    hotel_details_limit: int,
    model_name: str = "price_predictor",
) -> str:
    """
    Generates a consistent filename for the trained model.
    """
    return f"{ML_MODEL_DIR}/{destination}_{adults}_{rooms}_{properties_limit}_{hotel_details_limit}_{model_name}"
