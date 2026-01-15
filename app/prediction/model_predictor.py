from typing import Optional

import pandas as pd
import tensorflow as tf

from app.prediction.feature_engineering import extract_hotel_details_features
from app.prediction.model_loader import load_model_artifacts  # Import the new function
from app.utils.logger import logger
from app.scrapers.booking_com.orchestrator import _get_model_filename # Import the helper


async def predict_price(
    df_properties: pd.DataFrame,
    df_hotel_details: Optional[pd.DataFrame],
    model_type: str,
    destination: str,
    adults: int,
    rooms: int,
    limit: int, # properties_limit
    hotel_details_limit: int, # New parameter
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

    Returns:
        pd.DataFrame: DataFrame with predicted prices.
    """
    logger.info(f"Attempting to predict prices using {model_type} model.")

    # Generate the model filename consistently
    model_filename = _get_model_filename(destination, adults, rooms, limit, hotel_details_limit, model_name=model_type + "_price_predictor")

    # Load model, scalers, and metadata using the new loader function
    loaded_artifacts = load_model_artifacts(model_filename, model_type)
    model = loaded_artifacts["model"]
    scaler_X = loaded_artifacts["scaler_X"]
    scaler_y = loaded_artifacts["scaler_y"]
    meta = loaded_artifacts["meta"]

    feature_columns = meta["features"]
    currency = meta["currency"]

    # Prepare input data for prediction
    input_df = df_properties.copy()
    if model_type.lower() in ["advanced", "high"] and df_hotel_details is not None:
        advanced_features_df = extract_hotel_details_features(df_hotel_details)
        input_df = pd.merge(input_df, advanced_features_df, on="hotel_link", how="left")
        # Handle cases where manual entry might not have hotel_link for merge, or a simplified df_properties
        # In such cases, we assume a single input and map the ManualHotelData fields directly to feature_columns
        if "hotel_link" not in df_properties.columns and len(df_properties) == 1:
            input_df = (
                df_properties.copy()
            )  # Start with manual data which already has features mapped
            # Ensure advanced features are added if they were in the training meta
            for feature in advanced_features_df.columns:
                if feature not in input_df.columns:
                    # Try to get value from advanced_features_df for the first (and only) row
                    input_df[feature] = (
                        advanced_features_df[feature].iloc[0]
                        if not advanced_features_df.empty
                        else 0
                    )

    # Ensure all required feature columns are present, fill missing with 0 if necessary
    for col in feature_columns:
        if col not in input_df.columns:
            logger.warning(
                f"Missing feature '{col}' in input data. Setting to 0 for prediction."
            )
            input_df[col] = 0

    # Cast boolean-like features to int if they somehow became bool (e.g. from manual input)
    for col in feature_columns:
        if "has_" in col or "preferred_badge" in col:  # Identify binary features
            input_df[col] = input_df[col].astype(int)

    # Select and order features as per training metadata
    X_predict = input_df[feature_columns].values

    # Scale the input features
    X_predict_scaled = scaler_X.transform(X_predict)

    # Make predictions
    predictions_scaled = model.predict(X_predict_scaled)

    # Inverse transform to get actual prices
    predicted_prices = scaler_y.inverse_transform(predictions_scaled)

    # Create a DataFrame for results
    results_df = pd.DataFrame(predicted_prices, columns=["predicted_price"])
    results_df["currency"] = currency

    # If a 'name' column exists in input_df, add it to results
    if "name" in input_df.columns:
        results_df["name"] = input_df["name"]
    elif len(input_df) == 1 and "Manually Entered Hotel" in input_df["name"].values:
        results_df["name"] = "Manually Entered Hotel"  # For single manual entry

    logger.info("Price prediction completed.")
    return results_df
