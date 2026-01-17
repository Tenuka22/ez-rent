import os
import os
from typing import cast

import joblib
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.prediction.feature_engineering import extract_hotel_details_features
from app.utils.constants import ML_MODEL_DIR, get_model_filepath
from app.utils.logger import logger


async def train_advanced_model(
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
        advanced_features_df = extract_hotel_details_features(df_hotel_details)
        logger.debug(
            f"Advanced features extracted from hotel details:\n{advanced_features_df.head()}"
        )

        # Step 2: Merge property listings with advanced features
        # Ensure 'hotel_link' is the merge key, and it exists in both
        df_merged = pd.merge(
            df_properties,
            advanced_features_df,
            on="hotel_link",
            how="inner",
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
            10,
            min(25, num_samples // 3),  # Slightly more patience for advanced model
        )
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
        logger.info(f"Advanced model training completed.")

        logger.info(f"Final training loss: {history.history['loss'][-1]:.4f}")
        logger.info(f"Final validation loss: {history.history['val_loss'][-1]:.4f}")

        model_name_prefix = "advanced_price_predictor"
        model_filename_full = get_model_filepath(
            destination,
            adults,
            rooms,
            limit,
            hotel_details_limit=0, # Advanced model is not limited by hotel_details_limit directly for its name
            model_name=model_name_prefix
        )
        base_path = model_filename_full # The function already returns the full base path
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"Saving advanced model artifacts to: {base_path}")

        model.save(os.path.join(base_path, "tf_model.keras"))
        logger.debug("Advanced TensorFlow model saved.")

        joblib.dump(scaler_X, os.path.join(base_path, f"{model_name_prefix}_scaler_X.joblib"))
        joblib.dump(scaler_y, os.path.join(base_path, f"{model_name_prefix}_scaler_y.joblib"))
        logger.debug("Advanced scalers saved.")

        joblib.dump(
            {
                "features": feature_columns,  # Use dynamically generated feature_columns
                "target": target_column,
                "currency": currency,
            },
            os.path.join(base_path, f"{model_name_prefix}_meta.joblib"),
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


if __name__ == "__main__":
    import asyncio

    # Define paths to the scraped data
    properties_path = os.path.join(
        "scraped", "properties", str(destination), str(adults), str(rooms), f"limit_{limit}.csv"
    )
    hotel_details_path = os.path.join(
        "scraped", "hotel_details", str(destination), str(adults), str(rooms), f"limit_100.csv" # The original model used a hotel_details_limit of 100
    )

    # Load the datasets
    df_hotel_details = pd.read_csv(hotel_details_path)
    df_properties = pd.read_csv(properties_path)

    # Extract parameters from file names or define them manually
    destination = "Unawatuna"
    adults = 2
    rooms = 1
    limit = 300  # This corresponds to the properties limit

    # Run the asynchronous training function
    print("Running advanced training...")
    asyncio.run(
        train_advanced_model(
            df_properties=df_properties,
            df_hotel_details=df_hotel_details,
            destination=destination,
            adults=adults,
            rooms=rooms,
            limit=limit,
        )
    )
    print("Advanced training finished.")
