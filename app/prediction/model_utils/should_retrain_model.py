import os
from datetime import datetime, timedelta
from typing import Any, Dict

from app.prediction.model_utils.load_model_metadata import load_model_metadata
from app.utils.logger import logger


def should_retrain_model(
    model_filename: str,
    current_properties_count: int,
    current_hotel_details_count: int,
    min_data_increase_ratio: float = 0.1,  # 10% increase
    max_model_age_days: int = 30,  # 1 month
) -> bool:
    """
    Determines if a model should be retrained based on its age and the increase in available data.

    Args:
        model_filename (str): The base filename of the model.
        current_properties_count (int): The current number of property listings available.
        current_hotel_details_count (int): The current number of hotel details available.
        min_data_increase_ratio (float): The minimum ratio of data increase to trigger retraining.
        max_model_age_days (int): The maximum age of the model in days before retraining is recommended.

    Returns:
        bool: True if retraining is recommended, False otherwise.
    """
    metadata = load_model_metadata(model_filename)

    if not metadata:
        logger.info(
            f"No metadata found for model '{model_filename}'. Retraining recommended."
        )
        return True  # No metadata means no model or first run, so train it

    last_trained_str = metadata.get("last_trained_at")
    trained_properties_count = metadata.get("trained_properties_count", 0)
    trained_hotel_details_count = metadata.get("trained_hotel_details_count", 0)

    # Check model age
    if last_trained_str:
        last_trained_at = datetime.fromisoformat(last_trained_str)
        if datetime.now() - last_trained_at > timedelta(days=max_model_age_days):
            logger.info(
                f"Model '{model_filename}' is older than {max_model_age_days} days. Retraining recommended."
            )
            return True
    else:
        logger.warning(
            f"Metadata for '{model_filename}' missing 'last_trained_at'. Retraining recommended."
        )
        return True  # Missing timestamp, retrain

    # Check for significant data increase
    total_trained_data_points = trained_properties_count + trained_hotel_details_count
    total_current_data_points = current_properties_count + current_hotel_details_count

    if total_trained_data_points == 0:
        if total_current_data_points > 0:
            logger.info(
                f"Model '{model_filename}' was trained on zero data. Retraining recommended with new data."
            )
            return True
        else:
            # If both are zero, no new data to train on, and model was trained on zero,
            # then it's fine not to retrain if not stale.
            return False

    data_increase_ratio = (
        total_current_data_points - total_trained_data_points
    ) / total_trained_data_points
    if total_trained_data_points > 0 and data_increase_ratio > min_data_increase_ratio:
        logger.info(
            f"Data for model '{model_filename}' increased by {data_increase_ratio:.2f} "
            f"(trained: {total_trained_data_points}, current: {total_current_data_points}). "
            f"Exceeds threshold of {min_data_increase_ratio:.2f}. Retraining recommended."
        )
        return True

    logger.info(
        f"Model '{model_filename}' is up-to-date and not stale. No retraining needed."
    )
    return False
