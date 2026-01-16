import re
from typing import List

from playwright.async_api import Locator, Page

from app.data_models import PropertyListing
from app.scrapers.booking_com.parsers.extract_float_value import extract_float_value
from app.scrapers.booking_com.parsers.extract_price_components import (
    extract_price_components,
)
from app.scrapers.booking_com.parsers.parse_distance_km import parse_distance_km
from app.utils.logger import logger


async def extract_property_listing_from_card(card: Locator) -> PropertyListing:
    """
    Extracts detailed information for a single property listing from its card element.

    Args:
        card (Locator): Playwright Locator object for the property card.

    Returns:
        PropertyListing: A dataclass object containing the extracted property details.

    Raises:
        ValueError: If the property card link is not found.
    """
    # ---------- LINK ----------
    link = await card.locator('a[data-testid="title-link"]').get_attribute("href")

    if not link:
        logger.warning("No link found for property card, skipping extraction.")
        raise ValueError("Property card link not found.")

    if link.startswith("/"):
        link = f"https://www.booking.com{link}"

    # ---------- NAME ----------
    name_elem = card.locator('[data-testid="title"]')
    name = (await name_elem.inner_text()).strip() if await name_elem.count() else "N/A"

    # ---------- ADDRESS ----------
    address = None
    address_el = card.locator('[data-testid="address"]')
    if await address_el.count():
        address = (await address_el.inner_text()).strip()

    # ---------- STAR RATING ----------
    star_rating = 0.0  # Default value
    star_el = card.locator('[aria-label*="star"]')
    if await star_el.count():
        extracted_star_rating_text = await star_el.get_attribute("aria-label")
        if extracted_star_rating_text:
            # Extract number from "X-star hotel"
            match = re.search(r"(\d+)-star", extracted_star_rating_text)
            if match:
                star_rating = float(match.group(1))
            else:  # Fallback if no match or just extract the float value directly
                extracted_star_rating_value = extract_float_value(
                    extracted_star_rating_text
                )
                if extracted_star_rating_value is not None:
                    star_rating = extracted_star_rating_value

    # ---------- GUEST RATING ----------
    guest_rating_score = 0.0  # Default value
    rating_el = card.locator('[data-testid="review-score"] .bc946a29db')
    if await rating_el.count():
        extracted_score = extract_float_value(await rating_el.inner_text())
        if extracted_score is not None:
            guest_rating_score = extracted_score

    # ---------- REVIEW COUNT ----------
    reviews = 0.0  # Default value
    reviews_el = card.locator(
        '[data-testid="review-score"] .fff1944c52.fb14de7f14.eaa8455879'
    )
    if await reviews_el.count():
        reviews_text = (await reviews_el.inner_text()).strip()
        extracted_reviews_value = extract_float_value(reviews_text)
        if extracted_reviews_value is not None:
            reviews = extracted_reviews_value

    distance_from_downtown = None
    distance_from_beach = None

    # ---------- DISTANCE ----------
    downtown_el = card.locator('[data-testid="distance"]')

    if await downtown_el.count():
        text = (await downtown_el.first.inner_text()).lower()
        value = parse_distance_km(text)
        if value is not None:
            distance_from_downtown = value

    beach_el = card.locator("span.fff1944c52.d4d73793a3")

    if await beach_el.count():
        beach_text = (await beach_el.first.inner_text()).lower()

        if "beachfront" in beach_text:
            distance_from_beach = 0.0
        else:
            value = parse_distance_km(beach_text)
            if value is not None:
                distance_from_beach = value

    # ---------- PREFERRED BADGE ----------
    preferred_badge = 0  # Default value
    preferred_badge_el = card.locator('[data-testid="preferred-badge"]')
    if await preferred_badge_el.count():
        preferred_badge = 1

    # ---------- DEAL BADGE ----------
    deal_badge = 0  # Default value

    # Use the correct data-testid for the deal badge
    deal_badge_el = card.locator('[data-testid="property-card-deal"]')
    if await deal_badge_el.count():
        deal_badge = 1

    # ---------- PRICE (Values Only) ----------
    original_price_value = None
    original_price_currency = ""  # Default to empty string
    discounted_price_value = None
    discounted_price_currency = ""  # Default to empty string

    price_el_container = card.locator('[data-testid="price-and-discounted-price"]')
    if await price_el_container.count():
        full_price_text = await price_el_container.inner_text()

        # First, extract discounted price
        (
            extracted_discounted_value,
            extracted_discounted_currency,
        ) = extract_price_components(full_price_text)
        if extracted_discounted_value is not None:
            discounted_price_value = extracted_discounted_value
        if extracted_discounted_currency is not None:
            discounted_price_currency = extracted_discounted_currency

        # Now, try to find an explicit original price (e.g., strikethrough)
        original_price_el_explicit = card.locator(
            '[data-testid="price-and-discounted-price"] span[style*="line-through"], '
            '[data-testid="price-and-discounted-price"] span.prco-old-price, '
            '[data-testid="price-and-discounted-price"] span.e2e-original-price'
        )
        if await original_price_el_explicit.count():
            original_price_text = (
                await original_price_el_explicit.inner_text()
            ).strip()
            (
                extracted_original_value,
                extracted_original_currency,
            ) = extract_price_components(original_price_text)
            if extracted_original_value is not None:
                original_price_value = extracted_original_value
            if extracted_original_currency is not None:
                original_price_currency = extracted_original_currency

        # Fallback: If no explicit original price is found but discounted price is, assume original is same as discounted
        if original_price_value is None and discounted_price_value is not None:
            original_price_value = discounted_price_value
            original_price_currency = discounted_price_currency

    # ---------- TAXES (Values Only) ----------
    taxes_value = None
    taxes_currency = ""  # Default to empty string

    tax_el = card.locator('[data-testid="taxes-and-charges"]')
    if await tax_el.count():
        taxes_and_fees_text = (await tax_el.inner_text()).strip()
        (
            extracted_taxes_value,
            extracted_taxes_currency,
        ) = extract_price_components(taxes_and_fees_text)
        if extracted_taxes_value is not None:
            taxes_value = extracted_taxes_value
        if extracted_taxes_currency is not None:
            taxes_currency = extracted_taxes_currency

    # ---------- ROOM TYPE ----------
    room_type = ""  # Default value
    room_type_el = card.locator('h4[role="link"]')
    if await room_type_el.count():
        room_type = (await room_type_el.inner_text()).strip()

    # ---------- BED DETAILS ----------
    bed_details = ""  # Default value
    bed_details_el = card.locator("ul.d1e8dce286 li:first-child div.fff1944c52").nth(1)
    if await bed_details_el.count():
        bed_details = (await bed_details_el.inner_text()).strip()

    # ---------- CANCELLATION POLICY ----------
    cancellation_policy = ""  # Default value
    cancellation_el = card.locator(
        '[data-testid="cancellation-policy-icon"] + div div.cff4a33cd8'
    )
    if await cancellation_el.count():
        cancellation_policy = (await cancellation_el.inner_text()).strip()

    # ---------- PREPAYMENT POLICY ----------
    prepayment_policy = ""  # Default value
    prepayment_el = card.locator(
        '[data-testid="prepayment-policy-icon"] + div div.cff4a33cd8'
    )
    if await prepayment_el.count():
        prepayment_policy = (await prepayment_el.inner_text()).strip()

    # ---------- AVAILABILITY MESSAGE ----------
    availability_message = ""  # Default value
    availability_el = card.locator("ul.d1e8dce286 li:last-child div.b7d3eb6716")
    if await availability_el.count():
        availability_message = (await availability_el.inner_text()).strip()

    # ---------- NIGHTS AND GUESTS ----------
    nights_and_guests = ""  # Default value
    nights_and_guests_el = card.locator('[data-testid="price-for-x-nights"]')
    if await nights_and_guests_el.count():
        nights_and_guests = (await nights_and_guests_el.inner_text()).strip()

    return PropertyListing(
        name=name.strip(),
        hotel_link=link,
        address=address,
        star_rating=star_rating,
        guest_rating_score=guest_rating_score,
        reviews=reviews,
        distance_from_downtown=distance_from_downtown,
        distance_from_beach=distance_from_beach,
        preferred_badge=preferred_badge,
        deal_badge=deal_badge,
        room_type=room_type,
        bed_details=bed_details,
        cancellation_policy=cancellation_policy,
        prepayment_policy=prepayment_policy,
        availability_message=availability_message,
        nights_and_guests=nights_and_guests,
        original_price_value=original_price_value,
        original_price_currency=original_price_currency,
        discounted_price_value=discounted_price_value,
        discounted_price_currency=discounted_price_currency,
        taxes_and_fees_value=taxes_value,
        taxes_and_fees_currency=taxes_currency,
    )
