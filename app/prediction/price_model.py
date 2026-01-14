import os
from typing import cast

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
            df["discounted_price_value"], errors="coerce"
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
