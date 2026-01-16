import json
import os
from typing import Any, Dict

from app.prediction.model_utils.get_model_metadata_path import get_model_metadata_path
from app.utils.logger import logger


def load_model_metadata(model_filename: str) -> Dict[str, Any]:
    """
    Loads model metadata from a JSON file.

    Args:
        model_filename (str): The base filename of the model.

    Returns:
        Dict[str, Any]: A dictionary containing the loaded metadata, or an empty dictionary if not found/error.
    """
    metadata_path = get_model_metadata_path(model_filename)
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON metadata for {model_filename}: {e}")
            return {}
    return {}
