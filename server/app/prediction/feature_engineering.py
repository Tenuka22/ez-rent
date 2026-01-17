import pandas as pd
from typing import Any, Dict, List


def extract_hotel_details_features(df_hotel_details: pd.DataFrame) -> pd.DataFrame:
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