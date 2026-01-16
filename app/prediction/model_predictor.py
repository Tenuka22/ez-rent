from typing import Optional

import pandas as pd
import tensorflow as tf

from app.prediction.feature_engineering import extract_hotel_details_features
from app.prediction.model_loader import load_model_artifacts  # Import the new function
from app.utils.constants import (
    get_model_filepath,
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
    model_filename = get_model_filepath(
        destination,
        adults,
        rooms,
        limit,
        hotel_details_limit,
        model_name=model_type + "_price_predictor",
    )

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


if __name__ == "__main__":
    import asyncio
    import pandas as pd
    import os
    # from app.data_models import PropertyListing # These are not directly used here, but good for context
    # from app.data_models import HotelDetails # These are not directly used here, but good for context

    async def main():
        # Define the parameters that match how the model was trained
        destination = "Unawatuna"
        adults = 2
        rooms = 1
        properties_limit = 20 # Changed from 300 to 20
        hotel_details_limit = 10  # Changed from 100 to 10

        # Paths to the scraped data that the model would have been trained on
        # For demonstration, we'll try to load existing scraped data
        properties_path = os.path.join(
            "scraped", "properties", str(destination), str(adults), str(rooms), f"limit_{properties_limit}.csv"
        )
        hotel_details_path = os.path.join(
            "scraped", "hotel_details", str(destination), str(adults), str(rooms), f"limit_{hotel_details_limit}.csv"
        )
        
        df_properties = pd.DataFrame()
        df_hotel_details = None # Only for advanced model

        try:
            df_properties = pd.read_csv(properties_path)
            print(f"Loaded {len(df_properties)} properties from {properties_path}")
        except FileNotFoundError:
            print(f"Properties file not found at {properties_path}. Cannot perform prediction.")
            return

        # Prepare df_properties for a specific prediction if desired, or use the full df
        # For the user's request "Unawatuna Sunset Mirage Villa", let's filter for it
        target_hotel_name = "Sunset Mirage Villa" # From user prompt
        specific_property_df = df_properties[df_properties["name"].str.contains(target_hotel_name, case=False, na=False)]

        if specific_property_df.empty:
            print(f"Target hotel '{target_hotel_name}' not found in scraped properties. Using all properties for prediction.")
            df_properties_for_prediction = df_properties
        else:
            print(f"Found target hotel '{target_hotel_name}'. Predicting for this hotel.")
            df_properties_for_prediction = specific_property_df
        
        # Determine model type and load hotel details if using advanced model
        # For now, explicitly use basic model as that's what was last trained successfully with these limits
        model_type_to_use = "basic" 
        
        # Check if an advanced model exists for this configuration. 
        # Note: with current training flow, advanced model for limit=20, details=10 might not exist yet.
        advanced_model_name = "advanced_price_predictor"
        advanced_model_filepath = get_model_filepath(destination, adults, rooms, properties_limit, hotel_details_limit, model_name=advanced_model_name)
        
        if os.path.exists(os.path.join(advanced_model_filepath, "tf_model.keras")):
            print(f"Found advanced model artifacts at {advanced_model_filepath}. Attempting to use advanced model.")
            model_type_to_use = "advanced"
            
            try:
                df_hotel_details = pd.read_csv(hotel_details_path)
                print(f"Loaded {len(df_hotel_details)} hotel details from {hotel_details_path} for advanced model.")
            except FileNotFoundError:
                print(f"Hotel details file not found at {hotel_details_path}. Cannot perform advanced prediction. Falling back to basic model.")
                df_hotel_details = None
                model_type_to_use = "basic" # Fallback if hotel details not found for advanced
        else:
            print(f"No advanced model artifacts found at {advanced_model_filepath}. Using basic model.")


        print(f"Using model type: {model_type_to_use}")

        # Perform prediction
        predicted_df = await predict_price(
            df_properties=df_properties_for_prediction,
            df_hotel_details=df_hotel_details, # Pass hotel details for advanced model
            model_type=model_type_to_use, # Use the determined model type
            destination=destination,
            adults=adults,
            rooms=rooms,
            limit=properties_limit,
            hotel_details_limit=hotel_details_limit,
        )

        print("\nPredicted Prices:")
        print(predicted_df.to_string())

    asyncio.run(main())
