import os
from typing import cast

import joblib
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.utils.logger import logger


async def train_price_prediction_model(
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

        df = cast(
            pd.DataFrame,
            df[
                [
                    "discounted_price_value",
                    "taxes_and_fees_value",
                    "star_rating",
                    "guest_rating_score",
                    "distance_from_downtown",
                    "discounted_price_currency",
                ]
            ].copy(),
        )

        logger.debug(f"DataFrame head after column selection:\n{df.head()}")

        # Calculate full price
        df["full_price"] = df["discounted_price_value"] + df[
            "taxes_and_fees_value"
        ].fillna(0).infer_objects(copy=False)
        logger.debug("Calculated 'full_price' column.")

        # Drop rows with ANY missing values in required columns
        required_cols = [
            "full_price",
            "star_rating",
            "guest_rating_score",
            "distance_from_downtown",
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

        X = df[["star_rating", "guest_rating_score", "distance_from_downtown"]].values
        y = df["full_price"].values.reshape(-1, 1)  # Reshape for scaling

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

        # Scale target - THIS IS CRITICAL!
        logger.info("Scaling target variable.")
        scaler_y = StandardScaler()
        y_train_scaled = scaler_y.fit_transform(y_train)
        y_test_scaled = scaler_y.transform(y_test)
        logger.debug("Target variable scaled.")

        logger.info("Building TensorFlow Keras model.")
        model = tf.keras.Sequential(
            [
                tf.keras.layers.Dense(32, activation="relu", input_shape=(3,)),
                tf.keras.layers.Dropout(0.2),  # Add dropout for regularization
                tf.keras.layers.Dense(16, activation="relu"),
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.Dense(1),
            ]
        )

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="mse",
            metrics=["mae"],
        )
        logger.info("Model compiled successfully.")

        # Add early stopping
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=10, restore_best_weights=True
        )
        logger.info("Early stopping callback added.")

        logger.info("Starting model training.")
        history = model.fit(
            X_train_scaled,
            y_train_scaled,  # Use scaled target
            validation_data=(X_test_scaled, y_test_scaled),
            epochs=20,
            batch_size=min(16, len(X_train)),
            callbacks=[early_stopping],
            verbose=1,  # Set to 0 to prevent excessive console output from model.fit
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

        joblib.dump(
            {
                "features": [
                    "star_rating",
                    "guest_rating_score",
                    "distance_from_downtown",
                ],
                "target": "full_price",
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
