from dataclasses import dataclass
from typing import Any, Dict, Optional, List # Added List for typing_extensions compatibility


@dataclass
class PropertyListing:
    """Dataclass to hold scraped hotel data."""

    name: str
    hotel_link: Optional[str] = None  # Added hotel_link
    address: Optional[str] = None
    star_rating: Optional[float] = None
    guest_rating_score: Optional[float] = None
    reviews: Optional[float] = None
    distance_from_downtown: Optional[float] = None
    distance_from_beach: Optional[float] = None
    preferred_badge: Optional[int] = None
    deal_badge: Optional[int] = None
    room_type: str = ""
    bed_details: str = ""
    cancellation_policy: str = ""
    prepayment_policy: str = ""
    availability_message: str = ""
    nights_and_guests: str = ""
    original_price_value: Optional[float] = None
    original_price_currency: str = ""
    discounted_price_value: Optional[float] = None
    discounted_price_currency: str = ""
    taxes_and_fees_value: Optional[float] = None
    taxes_and_fees_currency: str = ""


@dataclass
class HotelDetails:
    """Complete hotel information data structure"""

    # Basic Information
    url: str
    name: Optional[str] = None
    star_rating: Optional[int] = None
    guest_rating: Optional[float] = None
    review_count: Optional[int] = None
    review_score_text: Optional[str] = None  # e.g., "Wonderful"

    # Location
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # lat, lng
    location_score: Optional[str] = None

    # Description
    description: Optional[str] = None
    property_highlights: Optional[List[str]] = None

    # Amenities & Facilities
    most_popular_facilities: Optional[List[str]] = None
    bathroom_facilities: Optional[List[str]] = None
    view_type: Optional[List[str]] = None
    outdoor_facilities: Optional[List[str]] = None
    kitchen_facilities: Optional[List[str]] = None
    room_amenities: Optional[List[str]] = None
    activities: Optional[List[str]] = None
    food_drink: Optional[List[str]] = None
    internet_info: Optional[str] = None
    parking_info: Optional[str] = None
    services: Optional[List[str]] = None
    safety_security: Optional[List[str]] = None
    general_facilities: Optional[List[str]] = None
    pool_info: Optional[Dict[str, Any]] = None
    spa_wellness: Optional[List[str]] = None
    languages_spoken: Optional[List[str]] = None


@dataclass
class ManualHotelData:
    """Dataclass for manually entering hotel data for price prediction."""
    # New fields for identification and compatibility
    name: str = "Manual Entry Hotel"  # Default name for manual entries
    hotel_link: str = "http://manual.entry.com" # Placeholder link

    # From PropertyListing (base features)
    star_rating: float = 0.0
    guest_rating_score: float = 0.0
    reviews: float = 0.0
    distance_from_downtown: float = 0.0
    distance_from_beach: float = 0.0
    preferred_badge: int = 0 # 0 or 1

    # From HotelDetails (advanced features) - directly as used by the model
    has_pool: int = 0 # 0 or 1
    has_free_wifi: int = 0 # 0 or 1
    has_free_parking: int = 0 # 0 or 1
    has_spa: int = 0 # 0 or 1
    description_length: int = 0
    num_popular_facilities: int = 0
    num_languages_spoken: int = 0
    has_restaurant: int = 0 # 0 or 1
    has_bar: int = 0 # 0 or 1
    has_breakfast: int = 0 # 0 or 1
    has_room_service: int = 0 # 0 or 1
    has_24hr_front_desk: int = 0 # 0 or 1
    has_airport_shuttle: int = 0 # 0 or 1
    has_family_rooms: int = 0 # 0 or 1
    has_air_conditioning_detail: int = 0 # 0 or 1
    has_non_smoking_rooms: int = 0 # 0 or 1
    has_private_bathroom: int = 0 # 0 or 1
    has_kitchenette: int = 0 # 0 or 1
    has_balcony: int = 0 # 0 or 1
    has_terrace: int = 0 # 0 or 1

    # To be compatible with the prediction logic that expects a DataFrame with 'discounted_price_currency'
    discounted_price_currency: str = "LKR" # Default or specify actual currency