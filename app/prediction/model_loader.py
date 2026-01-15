import os
from typing import Any, Dict

import joblib
import tensorflow as tf

from app.utils.logger import logger
from app.utils.constants import ML_MODEL_DIR # Import ML_MODEL_DIR


def load_model_artifacts(
    model_filename: str, model_type: str
) -> Dict[str, Any]:
    """
    Loads a trained model, its scalers, and metadata.

    Args:
        model_filename (str): The full filename of the model (e.g., "Unawatuna_2_1_100_10_price_predictor").

    Returns:
        Dict[str, Any]: A dictionary containing the loaded model, scaler_X, scaler_y, and metadata.

    Raises:
        FileNotFoundError: If any required model artifact is not found.
    """
    base_path = os.path.join(ML_MODEL_DIR, model_filename)
    model_path = os.path.join(base_path, "tf_model.keras")
    scaler_x_path = os.path.join(base_path, f"{model_filename}_scaler_X.joblib")
    scaler_y_path = os.path.join(base_path, f"{model_filename}_scaler_y.joblib")
    meta_path = os.path.join(base_path, f"{model_filename}_meta.joblib")

    # Check if all model artifacts exist
    if not all(
        os.path.exists(p) for p in [model_path, scaler_x_path, scaler_y_path, meta_path]
    ):
        raise FileNotFoundError(
            f"Model artifacts not found for {model_type} model at {base_path}. "
            "Please ensure the model has been trained first."
        )

    logger.info(f"Loading model artifacts for {model_type} model from {base_path}.")
    model = tf.keras.models.load_model(model_path)
    scaler_X = joblib.load(scaler_x_path)
    scaler_y = joblib.load(scaler_y_path)
    meta = joblib.load(meta_path)
    logger.info("Model artifacts loaded successfully.")

    return {"model": model, "scaler_X": scaler_X, "scaler_y": scaler_y, "meta": meta}
