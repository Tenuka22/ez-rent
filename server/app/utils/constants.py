import os
import re
from typing import List, Dict

# app/utils/constants.py

# Base directories
BASE_SCAPRED_DIR = "./scraped"
BASE_ML_DIR = "./ml_files"

# Templates for scraped data CSV file paths
PROPERTIES_CSV_PATH_TEMPLATE = (
    f"{BASE_SCAPRED_DIR}/properties/{{destination}}/{{adults}}/{{rooms}}/limit_{{limit}}.csv"
)
HOTEL_DETAILS_CSV_PATH_TEMPLATE = (
    f"{BASE_SCAPRED_DIR}/hotel_details/{{destination}}/{{adults}}/{{rooms}}/limit_{{limit}}.csv"
)

# Cache file path for URLs
URL_CSV_PATH = f"{BASE_SCAPRED_DIR}/urls.csv"

# Directory for storing machine learning model artifacts
ML_MODEL_DIR = BASE_ML_DIR


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
    filename = f"{destination}_{adults}_{rooms}_{properties_limit}_{hotel_details_limit}_{model_name}"
    return os.path.join(ML_MODEL_DIR, filename)


# Directory for storing prediction results
PREDICTIONS_DIR = os.path.join(BASE_SCAPRED_DIR, "predictions")


def get_prediction_filepath(
    destination: str,
    adults: int,
    rooms: int,
    properties_limit: int,
    hotel_details_limit: int,
    model_type: str,
    timestamp: str,
) -> str:
    """
    Constructs the file path for saving prediction results.
    """
    dir_path = os.path.join(
        PREDICTIONS_DIR,
        model_type,
        destination,
        str(adults),
        str(rooms),
        f"props_{properties_limit}",
        f"details_{hotel_details_limit}",
    )
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"predictions_{timestamp}.csv")


def get_all_prediction_files_metadata() -> List[Dict]:
    """
    Scans the PREDICTIONS_DIR for all prediction CSV files and extracts their metadata.
    Returns a list of dictionaries, where each dictionary represents a prediction file
    and contains its parsed metadata (model_type, destination, etc.) and full path.
    """
    all_predictions_metadata = []
    
    if not os.path.isdir(PREDICTIONS_DIR):
        return []

    for root, _, files in os.walk(PREDICTIONS_DIR):
        for file in files:
            if file.startswith("predictions_") and file.endswith(".csv"):
                # Extract timestamp from filename (e.g., predictions_YYYYMMDD_HHMMSS.csv)
                match = re.match(r"predictions_(\d{8}_\d{6})\.csv", file)
                if not match:
                    continue
                timestamp = match.group(1)

                # Extract parts relative to PREDICTIONS_DIR
                relative_path = os.path.relpath(root, PREDICTIONS_DIR)
                path_parts = relative_path.split(os.sep)

                # Expected path structure: model_type/destination/adults/rooms/props_LIMIT/details_LIMIT
                if len(path_parts) == 5:
                    model_type, destination, adults_str, rooms_str, limits_str = path_parts
                    
                    try:
                        adults = int(adults_str)
                        rooms = int(rooms_str)
                    except ValueError:
                        continue # Skip if adults or rooms are not integers

                    props_limit_match = re.match(r"props_(\d+)", limits_str)
                    details_limit_match = re.match(r"details_(\d+)", limits_str)

                    properties_limit = int(props_limit_match.group(1)) if props_limit_match else None
                    hotel_details_limit = int(details_limit_match.group(1)) if details_limit_match else None
                    
                    if properties_limit is None or hotel_details_limit is None:
                        continue # Skip if limits are not found or malformed

                    full_path = os.path.join(root, file)
                    
                    all_predictions_metadata.append({
                        "model_type": model_type,
                        "destination": destination,
                        "adults": adults,
                        "rooms": rooms,
                        "properties_limit": properties_limit,
                        "hotel_details_limit": hotel_details_limit,
                        "timestamp": timestamp,
                        "filename": file,
                        "full_path": full_path,
                    })
    return all_predictions_metadata


def get_all_property_files_metadata() -> List[Dict]:
    """
    Scans the BASE_SCAPRED_DIR/properties for all property CSV files and extracts their metadata.
    Returns a list of dictionaries with parsed metadata and the full file path.
    """
    all_properties_metadata = []
    properties_base_dir = os.path.join(BASE_SCAPRED_DIR, "properties")

    if not os.path.isdir(properties_base_dir):
        return []

    for root, _, files in os.walk(properties_base_dir):
        for file in files:
            if file.startswith("limit_") and file.endswith(".csv"):
                match = re.match(r"limit_(\d+)\.csv", file)
                if not match:
                    continue
                properties_limit = int(match.group(1))

                relative_path = os.path.relpath(root, properties_base_dir)
                path_parts = relative_path.split(os.sep)

                if len(path_parts) == 3:
                    destination, adults_str, rooms_str = path_parts
                    try:
                        adults = int(adults_str)
                        rooms = int(rooms_str)
                    except ValueError:
                        continue

                    full_path = os.path.join(root, file)
                    all_properties_metadata.append({
                        "destination": destination,
                        "adults": adults,
                        "rooms": rooms,
                        "properties_limit": properties_limit,
                        "full_path": full_path,
                    })
    return all_properties_metadata


def get_all_hotel_details_files_metadata() -> List[Dict]:
    """
    Scans the BASE_SCAPRED_DIR/hotel_details for all hotel details CSV files and extracts their metadata.
    Returns a list of dictionaries with parsed metadata and the full file path.
    """
    all_hotel_details_metadata = []
    hotel_details_base_dir = os.path.join(BASE_SCAPRED_DIR, "hotel_details")

    if not os.path.isdir(hotel_details_base_dir):
        return []

    for root, _, files in os.walk(hotel_details_base_dir):
        for file in files:
            if file.startswith("limit_") and file.endswith(".csv"):
                match = re.match(r"limit_(\d+)\.csv", file)
                if not match:
                    continue
                hotel_details_limit = int(match.group(1))

                relative_path = os.path.relpath(root, hotel_details_base_dir)
                path_parts = relative_path.split(os.sep)

                if len(path_parts) == 3:
                    destination, adults_str, rooms_str = path_parts
                    try:
                        adults = int(adults_str)
                        rooms = int(rooms_str)
                    except ValueError:
                        continue

                    full_path = os.path.join(root, file)
                    all_hotel_details_metadata.append({
                        "destination": destination,
                        "adults": adults,
                        "rooms": rooms,
                        "hotel_details_limit": hotel_details_limit,
                        "full_path": full_path,
                    })
    return all_hotel_details_metadata
