import os
from datetime import datetime
from typing import Optional

import pandas as pd
import tensorflow as tf

from app.prediction.feature_engineering import extract_hotel_details_features
from app.prediction.model_loader import load_model_artifacts
from app.utils.constants import (
    get_model_filepath,
    get_prediction_filepath,
)
from app.utils.logger import logger


async def predict_price(
    df_properties: pd.DataFrame,
    df_hotel_details: Optional[pd.DataFrame],
    model_type: str,
    destination: str,
    adults: int,
    rooms: int,
    limit: int,  # properties_limit
    hotel_details_limit: int,  # New parameter
    save_results: bool = True,
) -> pd.DataFrame:
    """
    Loads a trained model and predicts prices for new input data.

    Args:
        df_properties (pd.DataFrame): DataFrame containing property listing data.
        df_hotel_details (Optional[pd.DataFrame]): DataFrame containing detailed hotel data (for advanced model).
        model_type (str): Type of model to use ('basic' or 'advanced').
        destination (str): Destination used to save/load the model.
        adults (int): Number of adults used to save/load the model.
        rooms (int): Number of rooms used to save/load the model.
        limit (int): Limit used to save/load the model.
        hotel_details_limit (int): The limit for hotel details, used for model filename.
        save_results (bool): If True, saves prediction results to a CSV file.

    Returns:
        pd.DataFrame: DataFrame with predicted prices.
    """
    logger.info(f"Attempting to predict prices using {model_type} model.")

    model_filename = get_model_filepath(
        destination,
        adults,
        rooms,
        limit,
        hotel_details_limit,
        model_name=model_type + "_price_predictor",
    )

    loaded_artifacts = load_model_artifacts(model_filename, model_type)
    model = loaded_artifacts["model"]
    scaler_X = loaded_artifacts["scaler_X"]
    scaler_y = loaded_artifacts["scaler_y"]
    meta = loaded_artifacts["meta"]

    feature_columns = meta["features"]
    currency = meta["currency"]

    input_df = df_properties.copy()
    if model_type.lower() in ["advanced", "high"] and df_hotel_details is not None:
        advanced_features_df = extract_hotel_details_features(df_hotel_details)
        input_df = pd.merge(input_df, advanced_features_df, on="hotel_link", how="left")
        if "hotel_link" not in df_properties.columns and len(df_properties) == 1:
            input_df = (
                df_properties.copy()
            )  # Start with manual data which already has features mapped
            # Ensure advanced features are added if they were in the training meta
            for feature in advanced_features_df.columns:
                if feature not in input_df.columns:
                    input_df[feature] = (
                        advanced_features_df[feature].iloc[0]
                        if not advanced_features_df.empty
                        else 0
                    )

    for col in feature_columns:
        if col not in input_df.columns:
            logger.warning(
                f"Missing feature '{col}' in input data. Setting to 0 for prediction."
            )
            input_df[col] = 0

    for col in feature_columns:
        if "has_" in col or "preferred_badge" in col:  # Identify binary features
            input_df[col] = input_df[col].astype(int)

    X_predict = input_df[feature_columns].values
    X_predict_scaled = scaler_X.transform(X_predict)

    predictions_scaled = model.predict(X_predict_scaled)
    predicted_prices = scaler_y.inverse_transform(predictions_scaled)

    results_df = pd.DataFrame(predicted_prices, columns=["predicted_price"])
    results_df["currency"] = currency

    if "name" in input_df.columns:
        results_df["name"] = input_df["name"]
    elif len(input_df) == 1 and "Manually Entered Hotel" in input_df["name"].values:
        results_df["name"] = "Manually Entered Hotel"  # For single manual entry

    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = get_prediction_filepath(
            destination,
            adults,
            rooms,
            limit,
            hotel_details_limit,
            model_type,
            timestamp,
        )
        results_df.to_csv(filepath, index=False)
        logger.info(f"Prediction results saved to {filepath}")

    logger.info("Price prediction completed.")
    return results_df
