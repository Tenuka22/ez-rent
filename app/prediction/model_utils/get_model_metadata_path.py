import os

from app.utils.constants import ML_MODEL_DIR


def get_model_metadata_path(model_filename: str) -> str:
    """
    Constructs the file path for a model's metadata JSON file.

    Args:
        model_filename (str): The base filename of the model.

    Returns:
        str: The full path to the metadata JSON file.
    """
    return os.path.join(ML_MODEL_DIR, f"{model_filename}.json")
