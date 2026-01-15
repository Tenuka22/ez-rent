import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from app.utils.constants import ML_MODEL_DIR
from app.utils.logger import logger

def get_model_metadata_path(model_filename: str) -> str:
    """Constructs the path to the model's metadata JSON file."""
    return os.path.join(ML_MODEL_DIR, f"{model_filename}.json")

def load_model_metadata(model_filename: str) -> Dict[str, Any]:
    """Loads metadata for a given model if it exists, otherwise returns an empty dict."""
    metadata_path = get_model_metadata_path(model_filename)
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON metadata for {model_filename}: {e}")
            return {}
    return {}

def save_model_metadata(model_filename: str, metadata: Dict[str, Any]):
    """Saves metadata for a given model."""
    os.makedirs(ML_MODEL_DIR, exist_ok=True)
    metadata_path = get_model_metadata_path(model_filename)
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        logger.debug(f"Saved metadata for {model_filename} to {metadata_path}")
    except IOError as e:
        logger.error(f"Error saving metadata for {model_filename}: {e}")

def should_retrain_model(
    model_filename: str,
    current_properties_count: int,
    current_hotel_details_count: int,
    min_data_increase_ratio: float = 0.1,  # 10% increase
    max_model_age_days: int = 30,  # 1 month
) -> bool:
    """
    Determines if a model needs to be retrained based on age or new data availability.

    Args:
        model_filename: The base filename of the model (e.g., "Unawatuna_2_1_300_price_predictor").
        current_properties_count: The number of properties scraped in the current run.
        current_hotel_details_count: The number of hotel details scraped in the current run.
        min_data_increase_ratio: The ratio of data increase (e.g., 0.1 for 10%) to trigger retraining.
        max_model_age_days: The maximum age in days before a model is considered stale.

    Returns:
        True if the model should be retrained, False otherwise.
    """
    metadata = load_model_metadata(model_filename)

    if not metadata:
        logger.info(f"No metadata found for model '{model_filename}'. Retraining recommended.")
        return True  # No metadata means no model or first run, so train it

    last_trained_str = metadata.get("last_trained_at")
    trained_properties_count = metadata.get("trained_properties_count", 0)
    trained_hotel_details_count = metadata.get("trained_hotel_details_count", 0)

    # Check model age
    if last_trained_str:
        last_trained_at = datetime.fromisoformat(last_trained_str)
        if datetime.now() - last_trained_at > timedelta(days=max_model_age_days):
            logger.info(f"Model '{model_filename}' is older than {max_model_age_days} days. Retraining recommended.")
            return True
    else:
        logger.warning(f"Metadata for '{model_filename}' missing 'last_trained_at'. Retraining recommended.")
        return True # Missing timestamp, retrain

    # Check for significant data increase
    total_trained_data_points = trained_properties_count + trained_hotel_details_count
    total_current_data_points = current_properties_count + current_hotel_details_count

    if total_trained_data_points == 0:
        if total_current_data_points > 0:
            logger.info(f"Model '{model_filename}' was trained on zero data. Retraining recommended with new data.")
            return True
        else:
            # If both are zero, no new data to train on, and model was trained on zero,
            # then it's fine not to retrain if not stale.
            return False


    data_increase_ratio = (total_current_data_points - total_trained_data_points) / total_trained_data_points
    if data_increase_ratio > min_data_increase_ratio:
        logger.info(
            f"Data for model '{model_filename}' increased by {data_increase_ratio:.2f} "
            f"(trained: {total_trained_data_points}, current: {total_current_data_points}). "
            f"Exceeds threshold of {min_data_increase_ratio:.2f}. Retraining recommended."
        )
        return True

    logger.info(f"Model '{model_filename}' is up-to-date and not stale. No retraining needed.")
    return False

