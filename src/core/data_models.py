from dataclasses import dataclass
from typing import Any, Dict, Optional

from typing_extensions import List


@dataclass
class ScrapedData:
    """Dataclass to hold scraped hotel data."""

    name: str
    link: Optional[str] = None
    hotel_link: Optional[str] = None  # Added hotel_link
    address: Optional[str] = None
    star_rating: Optional[str] = None
    guest_rating_score: Optional[str] = None
    reviews: Optional[str] = None
    distance_from_downtown: Optional[str] = None
    distance_from_beach: Optional[str] = None
    preferred_badge: Optional[str] = None
    deal_badge: Optional[str] = None
    room_type: Optional[str] = None
    bed_details: Optional[str] = None
    cancellation_policy: Optional[str] = None
    prepayment_policy: Optional[str] = None
    availability_message: Optional[str] = None
    stay_dates: Optional[str] = None
    nights_and_guests: Optional[str] = None
    original_price: Optional[str] = None
    discounted_price: Optional[str] = None
    taxes_and_fees: Optional[str] = None


@dataclass
class HotelDetailData:
    """Complete hotel information data structure"""

    # Basic Information
    url: str
    name: Optional[str] = None
    star_rating: Optional[str] = None
    guest_rating: Optional[str] = None
    review_count: Optional[str] = None
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

    # Rooms
    room_types: Optional[List[str]] = None

    # Pricing
    price: Optional[str] = None

    # House Rules
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None

    # Media
    photos_count: Optional[str] = None
