from dataclasses import dataclass
from typing import Optional


@dataclass
class ScrapedData:
    """Dataclass to hold scraped hotel data."""

    name: str
    link: Optional[str] = None
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
