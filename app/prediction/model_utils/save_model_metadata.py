import json
import os
from typing import Any, Dict

from app.prediction.model_utils.get_model_metadata_path import get_model_metadata_path
from app.utils.constants import ML_MODEL_DIR
from app.utils.logger import logger


def save_model_metadata(model_filename: str, metadata: Dict[str, Any]):
    """
    Saves model metadata to a JSON file.

    Args:
        model_filename (str): The base filename of the model.
        metadata (Dict[str, Any]): The metadata dictionary to save.
    """
    os.makedirs(ML_MODEL_DIR, exist_ok=True)
    metadata_path = get_model_metadata_path(model_filename)
    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
        logger.debug(f"Saved metadata for {model_filename} to {metadata_path}")
    except IOError as e:
        logger.error(f"Error saving metadata for {model_filename}: {e}")
