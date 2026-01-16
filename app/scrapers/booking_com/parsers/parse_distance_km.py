from typing import Optional

from app.scrapers.booking_com.parsers.extract_float_value import extract_float_value


def parse_distance_km(value_string: str | None) -> float | None:
    """
    Parses a distance string and returns distance in kilometers.
    Supports:
      - '2.8 km from downtown' → 2.8
      - '350 m from beach' → 0.35
      - 'Beachfront' → 0.0

    Args:
        value_string (str | None): The input string containing distance information.

    Returns:
        float | None: The distance in kilometers, or None if parsing fails.
    """
    if not value_string:
        return None

    text = value_string.lower().strip()

    if "beachfront" in text:
        return 0.0

    value = extract_float_value(text)
    if value is None:
        return None

    if " m" in text or " meters" in text:
        return value / 1000

    return value
