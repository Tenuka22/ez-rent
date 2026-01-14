import os
from typing import Optional, cast

import joblib
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.utils.logger import logger


async def train_price_prediction_model_without_high_level_data(
    df: pd.DataFrame,
    destination: str,
    adults: int,
    rooms: int,
    limit: int,
) -> None:
    logger.info(
        f"Starting price predictor creation for destination='{destination}', "
        f"adults={adults}, rooms={rooms}, limit={limit}."
    )

    try:
        # Validate minimum data requirement
        if len(df) < 10:
            logger.warning(
                f"Insufficient data: only {len(df)} properties found. Need at least 10 for training."
            )
            raise Exception(
                f"Insufficient data: only {len(df)} properties found. Need at least 10 for training."
            )

        print(df.head())
        print(df.columns)

        # Fixed: Removed duplicate and added distance_from_beach
        df = cast(
            pd.DataFrame,
            df[
                [
                    "star_rating",
                    "guest_rating_score",
                    "reviews",
                    "distance_from_downtown",
                    "distance_from_beach",
                    "preferred_badge",
                    "discounted_price_value",
                    "discounted_price_currency",
                ]
            ].copy(),
        )

        logger.debug(f"DataFrame head after column selection:\n{df.head()}")

        df["discounted_price_value"] = pd.to_numeric(
            df["discounted_price_value"],
            errors="coerce",
        ).fillna(0)
        logger.debug("Converted 'discounted_price' to numeric and filled NaNs.")

        # Fixed: Updated required_cols to match actual columns
        required_cols = [
            "star_rating",
            "guest_rating_score",
            "reviews",
            "distance_from_downtown",
            "distance_from_beach",
            "preferred_badge",
            "discounted_price_value",
        ]

        initial_rows = len(df)
        df.dropna(subset=required_cols, inplace=True)
        logger.info(
            f"Dropped {initial_rows - len(df)} rows with missing values. "
            f"Remaining properties: {len(df)}"
        )

        # Check if we still have enough data after cleaning
        if len(df) < 10:
            logger.warning(
                f"Insufficient valid data after cleaning: only {len(df)} properties remain. Need at least 10."
            )
            raise Exception(
                f"Insufficient valid data after cleaning: only {len(df)} properties remain. Need at least 10."
            )

        # Fixed: Updated feature selection to include distance_from_beach
        X = df[
            [
                "star_rating",
                "guest_rating_score",
                "reviews",
                "distance_from_downtown",
                "distance_from_beach",
                "preferred_badge",
            ]
        ].values
        y = df["discounted_price_value"]

        logger.info(f"Training with {len(X)} properties")
        logger.debug(f"Feature matrix shape: {X.shape}")
        logger.debug(f"Price range: {y.min():.2f} - {y.max():.2f}")

        # Determine currency
        currency = "N/A"
        if (
            not df["discounted_price_currency"].empty
            and df["discounted_price_currency"].iloc[0] is not None
        ):
            currency = df["discounted_price_currency"].iloc[0]
        logger.info(f"Determined currency: {currency}")

        # Need at least 5 samples to do a train/test split
        if len(X) < 5:
            logger.warning(f"Not enough data for train/test split: {len(X)} samples.")
            raise Exception(f"Not enough data for train/test split: {len(X)} samples")

        logger.info("Performing train/test split.")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        logger.debug(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")

        # Scale features
        logger.info("Scaling features.")
        scaler_X = StandardScaler()
        X_train_scaled = scaler_X.fit_transform(X_train)
        X_test_scaled = scaler_X.transform(X_test)
        logger.debug("Features scaled.")

        # Scale target - CRITICAL FIX: Reshape to 2D array
        logger.info("Scaling target variable.")
        scaler_y = StandardScaler()
        y_train_scaled = scaler_y.fit_transform(y_train.values.reshape(-1, 1))
        y_test_scaled = scaler_y.transform(y_test.values.reshape(-1, 1))
        logger.debug("Target variable scaled.")

        logger.info("Building TensorFlow Keras model.")

        # Dynamic model architecture based on dataset size
        num_samples = len(X_train)

        # Scale model complexity with data size
        # Small datasets (< 30): simpler model
        # Medium datasets (30-100): moderate complexity
        # Large datasets (> 100): full complexity
        if num_samples < 30:
            first_layer = min(32, num_samples * 2)
            second_layer = min(16, num_samples)
            dropout_rate = 0.2
        elif num_samples < 100:
            first_layer = 64
            second_layer = 32
            dropout_rate = 0.3
        else:
            first_layer = 128
            second_layer = 64
            dropout_rate = 0.4

        logger.info(
            f"Dynamic model architecture: [{first_layer}, {second_layer}] "
            f"with dropout={dropout_rate} for {num_samples} training samples"
        )

        model = tf.keras.Sequential(
            [
                tf.keras.layers.Dense(first_layer, activation="relu"),
                tf.keras.layers.Dropout(dropout_rate),
                tf.keras.layers.Dense(second_layer, activation="relu"),
                tf.keras.layers.Dropout(dropout_rate),
                tf.keras.layers.Dense(1),
            ]
        )

        # Fixed: Removed 'accuracy' metric (not suitable for regression)
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="mse",
            metrics=["mae"],
        )
        logger.info("Model compiled successfully.")

        # Add early stopping with dynamic patience based on dataset size
        # Smaller datasets need more patience as they're more volatile
        patience = max(10, min(20, num_samples // 3))
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=patience, restore_best_weights=True
        )
        logger.info(f"Early stopping callback added with patience={patience}.")

        logger.info("Starting model training.")

        # Dynamic epochs based on dataset size
        # Smaller datasets need more epochs to learn patterns
        if num_samples < 30:
            epochs = 100
        elif num_samples < 100:
            epochs = 50
        else:
            epochs = 30

        logger.info(
            f"Training for up to {epochs} epochs (early stopping may end training sooner)"
        )

        history = model.fit(
            X_train_scaled,
            y_train_scaled,
            validation_data=(X_test_scaled, y_test_scaled),
            epochs=epochs,
            batch_size=min(16, len(X_train)),
            callbacks=[early_stopping],
            verbose=1,
        )
        logger.info("Model training completed.")

        logger.info(f"Final training loss: {history.history['loss'][-1]:.4f}")
        logger.info(f"Final validation loss: {history.history['val_loss'][-1]:.4f}")

        model_name = "price_predictor"
        base_path = f"./ml_files/{destination}/{adults}/{rooms}/{limit}/{model_name}"
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"Saving model artifacts to: {base_path}")

        model.save(os.path.join(base_path, "tf_model.keras"))
        logger.debug("TensorFlow model saved.")

        # Save BOTH scalers
        joblib.dump(scaler_X, os.path.join(base_path, f"{model_name}_scaler_X.joblib"))
        joblib.dump(scaler_y, os.path.join(base_path, f"{model_name}_scaler_y.joblib"))
        logger.debug("Scalers saved.")

        # Fixed: Updated metadata to include all 6 features
        joblib.dump(
            {
                "features": [
                    "star_rating",
                    "guest_rating_score",
                    "reviews",
                    "distance_from_downtown",
                    "distance_from_beach",
                    "preferred_badge",
                ],
                "target": "discounted_price_value",
                "currency": currency,
            },
            os.path.join(base_path, f"{model_name}_meta.joblib"),
        )
        logger.debug("Metadata saved.")

        logger.info("Price predictor created and saved successfully.")
        return None

    except Exception as e:
        logger.error(
            f"Error creating price predictor for destination='{destination}': {e}",
            exc_info=True,
        )
        raise Exception(f"Error creating price predictor: {str(e)}")


def _extract_hotel_details_features(df_hotel_details: pd.DataFrame) -> pd.DataFrame:
    """Extracts additional features from hotel details for advanced model."""
    features_df = pd.DataFrame()

    features_df["hotel_link"] = df_hotel_details[
        "url"
    ]  # Use url from HotelDetails for merging

    # Boolean features (general)
    features_df["has_pool"] = df_hotel_details["pool_info"].apply(
        lambda x: 1 if isinstance(x, dict) and "type" in x else 0
    )
    features_df["has_free_wifi"] = df_hotel_details["internet_info"].apply(
        lambda x: 1 if isinstance(x, str) and "free wifi" in x.lower() else 0
    )
    features_df["has_free_parking"] = df_hotel_details["parking_info"].apply(
        lambda x: 1 if isinstance(x, str) and "free parking" in x.lower() else 0
    )
    features_df["has_spa"] = df_hotel_details["spa_wellness"].apply(
        lambda x: 1 if isinstance(x, list) and len(x) > 0 else 0
    )

    # Numerical features
    features_df["description_length"] = df_hotel_details["description"].apply(
        lambda x: len(x) if isinstance(x, str) else 0
    )
    features_df["num_popular_facilities"] = df_hotel_details[
        "most_popular_facilities"
    ].apply(lambda x: len(x) if isinstance(x, list) else 0)
    features_df["num_languages_spoken"] = df_hotel_details["languages_spoken"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )

    # More granular boolean features from list-based facilities
    # Helper lambda for checking presence in a list of strings
    has_feature = (
        lambda lst, keyword: 1
        if isinstance(lst, list) and any(keyword in item.lower() for item in lst)
        else 0
    )

    features_df["has_restaurant"] = df_hotel_details["food_drink"].apply(
        lambda x: has_feature(x, "restaurant")
    )
    features_df["has_bar"] = df_hotel_details["food_drink"].apply(
        lambda x: has_feature(x, "bar")
    )
    features_df["has_breakfast"] = df_hotel_details["food_drink"].apply(
        lambda x: has_feature(x, "breakfast")
    )
    features_df["has_room_service"] = df_hotel_details["services"].apply(
        lambda x: has_feature(x, "room service")
    )
    features_df["has_24hr_front_desk"] = df_hotel_details["services"].apply(
        lambda x: has_feature(x, "24-hour front desk")
    )
    features_df["has_airport_shuttle"] = df_hotel_details["general_facilities"].apply(
        lambda x: has_feature(x, "airport shuttle")
    )
    features_df["has_family_rooms"] = df_hotel_details["general_facilities"].apply(
        lambda x: has_feature(x, "family rooms")
    )
    features_df["has_air_conditioning_detail"] = df_hotel_details[
        "general_facilities"
    ].apply(  # Renamed to avoid collision
        lambda x: has_feature(x, "air conditioning")
    )
    features_df["has_non_smoking_rooms"] = df_hotel_details["general_facilities"].apply(
        lambda x: has_feature(x, "non-smoking rooms")
    )
    features_df["has_private_bathroom"] = df_hotel_details["bathroom_facilities"].apply(
        lambda x: has_feature(x, "private bathroom")
    )
    features_df["has_kitchenette"] = df_hotel_details["kitchen_facilities"].apply(
        lambda x: has_feature(x, "kitchenette")
        or has_feature(x, "kitchen")  # Check for both
    )
    features_df["has_balcony"] = df_hotel_details["outdoor_facilities"].apply(
        lambda x: has_feature(x, "balcony")
    )
    features_df["has_terrace"] = df_hotel_details["outdoor_facilities"].apply(
        lambda x: has_feature(x, "terrace")
    )

    return features_df


async def train_advanced_price_prediction_model(
    df_properties: pd.DataFrame,
    df_hotel_details: pd.DataFrame,
    destination: str,
    adults: int,
    rooms: int,
    limit: int,
) -> None:
    logger.info(
        f"Starting advanced price predictor creation for destination='{destination}', "
        f"adults={adults}, rooms={rooms}, limit={limit}."
    )

    try:
        # Step 1: Extract features from hotel details
        advanced_features_df = _extract_hotel_details_features(df_hotel_details)
        logger.debug(
            f"Advanced features extracted from hotel details:\n{advanced_features_df.head()}"
        )

        # Step 2: Merge property listings with advanced features
        # Ensure 'hotel_link' is the merge key, and it exists in both
        df_merged = pd.merge(
            df_properties, advanced_features_df, on="hotel_link", how="inner"
        )
        logger.info(f"Merged DataFrame shape: {df_merged.shape}")
        logger.debug(f"Merged DataFrame head:\n{df_merged.head()}")

        # Validate minimum data requirement after merge
        if len(df_merged) < 10:
            logger.warning(
                f"Insufficient data after merge: only {len(df_merged)} properties remain. "
                f"Need at least 10 for training."
            )
            raise Exception(
                f"Insufficient data after merge: only {len(df_merged)} properties remain. "
                f"Need at least 10 for training."
            )

        # Select relevant columns for the model
        # Combined features from both property listings and advanced details
        feature_columns = [
            "star_rating",
            "guest_rating_score",
            "reviews",
            "distance_from_downtown",
            "distance_from_beach",
            "preferred_badge",
            # New advanced features (general)
            "has_pool",
            "has_free_wifi",
            "has_free_parking",
            "has_spa",
            "description_length",
            "num_popular_facilities",
            "num_languages_spoken",
            # More granular boolean features
            "has_restaurant",
            "has_bar",
            "has_breakfast",
            "has_room_service",
            "has_24hr_front_desk",
            "has_airport_shuttle",
            "has_family_rooms",
            "has_air_conditioning_detail",
            "has_non_smoking_rooms",
            "has_private_bathroom",
            "has_kitchenette",
            "has_balcony",
            "has_terrace",
        ]
        target_column = "discounted_price_value"

        # Ensure all feature columns exist and convert target to numeric
        for col in feature_columns:
            if col not in df_merged.columns:
                logger.warning(
                    f"Missing feature column after merge: {col}. Setting to 0."
                )
                df_merged[col] = 0  # Default missing features to 0

        df_merged[target_column] = pd.to_numeric(
            df_merged[target_column],
            errors="coerce",
        ).fillna(0)  # Fill NaNs for target

        # Drop rows with any missing values in the final feature set or target
        initial_rows = len(df_merged)
        df_merged.dropna(subset=feature_columns + [target_column], inplace=True)
        logger.info(
            f"Dropped {initial_rows - len(df_merged)} rows with missing values after final feature selection. "
            f"Remaining properties: {len(df_merged)}"
        )

        # Check if we still have enough data after cleaning
        if len(df_merged) < 10:
            logger.warning(
                f"Insufficient valid data after cleaning: only {len(df_merged)} properties remain. Need at least 10."
            )
            raise Exception(
                f"Insufficient valid data after cleaning: only {len(df_merged)} properties remain. Need at least 10."
            )

        X = df_merged[feature_columns].values
        y = df_merged[target_column]

        logger.info(f"Training advanced model with {len(X)} properties.")
        logger.debug(f"Feature matrix shape: {X.shape}")
        logger.debug(f"Price range: {y.min():.2f} - {y.max():.2f}")

        # Determine currency
        currency = "N/A"
        if (
            not df_merged["discounted_price_currency"].empty
            and df_merged["discounted_price_currency"].iloc[0] is not None
        ):
            currency = df_merged["discounted_price_currency"].iloc[0]
        logger.info(f"Determined currency: {currency}")

        # Need at least 5 samples to do a train/test split
        if len(X) < 5:
            logger.warning(f"Not enough data for train/test split: {len(X)} samples.")
            raise Exception(f"Not enough data for train/test split: {len(X)} samples")

        logger.info("Performing train/test split for advanced model.")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        logger.debug(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")

        # Scale features
        logger.info("Scaling features for advanced model.")
        scaler_X = StandardScaler()
        X_train_scaled = scaler_X.fit_transform(X_train)
        X_test_scaled = scaler_X.transform(X_test)
        logger.debug("Features scaled.")

        # Scale target
        logger.info("Scaling target variable for advanced model.")
        scaler_y = StandardScaler()
        y_train_scaled = scaler_y.fit_transform(y_train.values.reshape(-1, 1))
        y_test_scaled = scaler_y.transform(y_test.values.reshape(-1, 1))
        logger.debug("Target variable scaled.")

        logger.info("Building TensorFlow Keras model for advanced prediction.")

        # Dynamic model architecture based on dataset size
        num_samples = len(X_train)
        if num_samples < 30:
            first_layer = min(64, num_samples * 2)
            second_layer = min(32, num_samples)
            dropout_rate = 0.2
        elif num_samples < 100:
            first_layer = 128
            second_layer = 64
            dropout_rate = 0.3
        else:
            first_layer = 256
            second_layer = 128
            dropout_rate = 0.4

        logger.info(
            f"Dynamic advanced model architecture: [{first_layer}, {second_layer}] "
            f"with dropout={dropout_rate} for {num_samples} training samples"
        )

        model = tf.keras.Sequential(
            [
                tf.keras.layers.Dense(first_layer, activation="relu"),
                tf.keras.layers.Dropout(dropout_rate),
                tf.keras.layers.Dense(second_layer, activation="relu"),
                tf.keras.layers.Dropout(dropout_rate),
                tf.keras.layers.Dense(1),
            ]
        )

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="mse",
            metrics=["mae"],
        )
        logger.info("Advanced model compiled successfully.")

        patience = max(
            10, min(25, num_samples // 3)
        )  # Slightly more patience for advanced model
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=patience, restore_best_weights=True
        )
        logger.info(f"Early stopping callback added with patience={patience}.")

        logger.info("Starting advanced model training.")
        if num_samples < 30:
            epochs = 150  # More epochs for smaller datasets
        elif num_samples < 100:
            epochs = 80
        else:
            epochs = 50

        logger.info(
            f"Training for up to {epochs} epochs (early stopping may end training sooner)"
        )

        history = model.fit(
            X_train_scaled,
            y_train_scaled,
            validation_data=(X_test_scaled, y_test_scaled),
            epochs=epochs,
            batch_size=min(16, len(X_train)),
            callbacks=[early_stopping],
            verbose=1,
        )
        logger.info("Advanced model training completed.")

        logger.info(f"Final training loss: {history.history['loss'][-1]:.4f}")
        logger.info(f"Final validation loss: {history.history['val_loss'][-1]:.4f}")

        model_name = "advanced_price_predictor"  # New model name
        base_path = f"./ml_files/{destination}/{adults}/{rooms}/{limit}/{model_name}"
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"Saving advanced model artifacts to: {base_path}")

        model.save(os.path.join(base_path, "tf_model.keras"))
        logger.debug("Advanced TensorFlow model saved.")

        joblib.dump(scaler_X, os.path.join(base_path, f"{model_name}_scaler_X.joblib"))
        joblib.dump(scaler_y, os.path.join(base_path, f"{model_name}_scaler_y.joblib"))
        logger.debug("Advanced scalers saved.")

        joblib.dump(
            {
                "features": feature_columns,  # Use dynamically generated feature_columns
                "target": target_column,
                "currency": currency,
            },
            os.path.join(base_path, f"{model_name}_meta.joblib"),
        )
        logger.debug("Advanced metadata saved.")

        logger.info("Advanced price predictor created and saved successfully.")
        return None

    except Exception as e:
        logger.error(
            f"Error creating advanced price predictor for destination='{destination}': {e}",
            exc_info=True,
        )
        raise Exception(f"Error creating advanced price predictor: {str(e)}")


def _extract_hotel_details_features(df_hotel_details: pd.DataFrame) -> pd.DataFrame:
    """Extracts additional features from hotel details for advanced model."""
    features_df = pd.DataFrame()

    features_df["hotel_link"] = df_hotel_details[
        "url"
    ]  # Use url from HotelDetails for merging

    # Boolean features (general)
    features_df["has_pool"] = df_hotel_details["pool_info"].apply(
        lambda x: 1 if isinstance(x, dict) and "type" in x else 0
    )
    features_df["has_free_wifi"] = df_hotel_details["internet_info"].apply(
        lambda x: 1 if isinstance(x, str) and "free wifi" in x.lower() else 0
    )
    features_df["has_free_parking"] = df_hotel_details["parking_info"].apply(
        lambda x: 1 if isinstance(x, str) and "free parking" in x.lower() else 0
    )
    features_df["has_spa"] = df_hotel_details["spa_wellness"].apply(
        lambda x: 1 if isinstance(x, list) and len(x) > 0 else 0
    )

    # Numerical features
    features_df["description_length"] = df_hotel_details["description"].apply(
        lambda x: len(x) if isinstance(x, str) else 0
    )
    features_df["num_popular_facilities"] = df_hotel_details[
        "most_popular_facilities"
    ].apply(lambda x: len(x) if isinstance(x, list) else 0)
    features_df["num_languages_spoken"] = df_hotel_details["languages_spoken"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )

    # More granular boolean features from list-based facilities
    # Helper lambda for checking presence in a list of strings
    has_feature = (
        lambda lst, keyword: 1
        if isinstance(lst, list) and any(keyword in item.lower() for item in lst)
        else 0
    )

    features_df["has_restaurant"] = df_hotel_details["food_drink"].apply(
        lambda x: has_feature(x, "restaurant")
    )
    features_df["has_bar"] = df_hotel_details["food_drink"].apply(
        lambda x: has_feature(x, "bar")
    )
    features_df["has_breakfast"] = df_hotel_details["food_drink"].apply(
        lambda x: has_feature(x, "breakfast")
    )
    features_df["has_room_service"] = df_hotel_details["services"].apply(
        lambda x: has_feature(x, "room service")
    )
    features_df["has_24hr_front_desk"] = df_hotel_details["services"].apply(
        lambda x: has_feature(x, "24-hour front desk")
    )
    features_df["has_airport_shuttle"] = df_hotel_details["general_facilities"].apply(
        lambda x: has_feature(x, "airport shuttle")
    )
    features_df["has_family_rooms"] = df_hotel_details["general_facilities"].apply(
        lambda x: has_feature(x, "family rooms")
    )
    features_df["has_air_conditioning_detail"] = df_hotel_details[
        "general_facilities"
    ].apply(  # Renamed to avoid collision
        lambda x: has_feature(x, "air conditioning")
    )
    features_df["has_non_smoking_rooms"] = df_hotel_details["general_facilities"].apply(
        lambda x: has_feature(x, "non-smoking rooms")
    )
    features_df["has_private_bathroom"] = df_hotel_details["bathroom_facilities"].apply(
        lambda x: has_feature(x, "private bathroom")
    )
    features_df["has_kitchenette"] = df_hotel_details["kitchen_facilities"].apply(
        lambda x: has_feature(x, "kitchenette")
        or has_feature(x, "kitchen")  # Check for both
    )
    features_df["has_balcony"] = df_hotel_details["outdoor_facilities"].apply(
        lambda x: has_feature(x, "balcony")
    )
    features_df["has_terrace"] = df_hotel_details["outdoor_facilities"].apply(
        lambda x: has_feature(x, "terrace")
    )

    return features_df


async def predict_price(
    df_properties: pd.DataFrame,
    df_hotel_details: Optional[pd.DataFrame],
    model_type: str,
    destination: str,
    adults: int,
    rooms: int,
    limit: int,
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

    Returns:
        pd.DataFrame: DataFrame with predicted prices.
    """
    logger.info(f"Attempting to predict prices using {model_type} model.")

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

    # Load model, scalers, and metadata
    model = tf.keras.models.load_model(model_path)
    scaler_X = joblib.load(scaler_x_path)
    scaler_y = joblib.load(scaler_y_path)
    meta = joblib.load(meta_path)

    feature_columns = meta["features"]
    currency = meta["currency"]

    # Prepare input data for prediction
    input_df = df_properties.copy()
    if model_type.lower() in ["advanced", "high"] and df_hotel_details is not None:
        advanced_features_df = _extract_hotel_details_features(df_hotel_details)
        input_df = pd.merge(input_df, advanced_features_df, on="hotel_link", how="left")
        # Handle cases where manual entry might not have hotel_link for merge, or a simplified df_properties
        # If df_properties is from manual entry, it might not have 'hotel_link' or other PropertyListing fields
        # In such cases, we assume a single input and map the ManualHotelData fields directly to feature_columns
        if not "hotel_link" in df_properties.columns and len(df_properties) == 1:
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
