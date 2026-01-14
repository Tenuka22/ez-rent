from dataclasses import dataclass
from typing import Any, Dict, Optional

from typing_extensions import List


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
