def normalize_booking_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    return url.split("?")[0].strip()