import os
import joblib
import tensorflow as tf
from typing import Dict, Any

from app.utils.logger import logger

def load_model_artifacts(model_type: str, destination: str, adults: int, rooms: int, limit: int) -> Dict[str, Any]:
    """
    Loads a trained model, its scalers, and metadata.

    Args:
        model_type (str): Type of model to use ('basic' or 'advanced').
        destination (str): Destination used to save/load the model.
        adults (int): Number of adults used to save/load the model.
        rooms (int): Number of rooms used to save/load the model.
        limit (int): Limit used to save/load the model.

    Returns:
        Dict[str, Any]: A dictionary containing the loaded model, scaler_X, scaler_y, and metadata.
    
    Raises:
        ValueError: If an unknown model_type is provided.
        FileNotFoundError: If any required model artifact is not found.
    """
    if model_type.lower() in ["basic", "low"]:
        model_name = "price_predictor"
    elif model_type.lower() in ["advanced", "high"]:
        model_name = "advanced_price_predictor"
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    base_path = f"./ml_files/{destination}/{adults}/{rooms}/{limit}/{model_name}"
    model_path = os.path.join(base_path, "tf_model.keras")
    scaler_x_path = os.path.join(base_path, f"{model_name}_scaler_X.joblib")
    scaler_y_path = os.path.join(base_path, f"{model_name}_scaler_y.joblib")
    meta_path = os.path.join(base_path, f"{model_name}_meta.joblib")

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

    return {
        "model": model,
        "scaler_X": scaler_X,
        "scaler_y": scaler_y,
        "meta": meta
    }
