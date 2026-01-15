import re
from typing import Optional

from playwright.async_api import Page

from app.data_models import HotelDetails, PropertyListing
from app.utils.logger import logger
from app.scrapers.booking_com.playwright_urls import BookingComUrls
from app.scrapers.booking_com.navigation import goto_properties_page
from app.scrapers.booking_com.parsers.data_parsers import (
    extract_float_value,
    extract_price_components,
    parse_distance_km,
)
from app.scrapers.booking_com.extractors.hotel_details_extractor import scrape_hotel_data


async def scrape_specific_property_data(
    page: Page,
    destination: str,
    adults: int,
    rooms: int,
    target_hotel_name: str,
) -> tuple[Optional[PropertyListing], Optional[HotelDetails]]:
    """
    Navigates to the search results page, finds a specific hotel by name,
    scrapes its PropertyListing and HotelDetails.
    """
    logger.info(f"Searching for specific hotel: '{target_hotel_name}'")

    urls = BookingComUrls()
    await goto_properties_page(
        page=page,
        destination=destination,
        urls=urls,
        adults=adults,
        rooms=rooms,
    )

    await page.wait_for_load_state("networkidle", timeout=60_000)
    await page.wait_for_selector('[data-testid="property-card"]', timeout=30_000)

    target_property_listing: Optional[PropertyListing] = None
    target_hotel_details: Optional[HotelDetails] = None

    # First, try to find the specific hotel in the currently loaded properties
    cards = page.locator('[data-testid="property-card"]')
    count = await cards.count()

    for i in range(count):
        card = cards.nth(i)
        name_elem = card.locator('[data-testid="title"]')
        if await name_elem.count() > 0:
            name = (await name_elem.inner_text()).strip()
            if name == target_hotel_name: # Exact match
                logger.info(f"Found specific hotel '{target_hotel_name}' on search results page.")
                
                # Extract PropertyListing details for the specific hotel
                try:
                    link = await card.locator('a[data-testid="title-link"]').get_attribute("href")
                    if not link: continue
                    if link.startswith("/"): link = f"https://www.booking.com{link}"

                    address_el = card.locator('[data-testid="address"]')
                    address = (await address_el.inner_text()).strip() if await address_el.count() else None

                    star_rating_text = await card.locator('[aria-label*="star"]').get_attribute("aria-label")
                    star_rating = float(re.search(r"(\d+)", star_rating_text).group(1)) if star_rating_text and re.search(r"(\d+)", star_rating_text) else 0.0

                    guest_rating_score = extract_float_value(await card.locator('[data-testid="review-score"] .bc946a29db').inner_text())
                    reviews = extract_float_value(await card.locator('[data-testid="review-score"] .fff1944c52.fb14de7f14.eaa8455879').inner_text())

                    downtown_el = card.locator('[data-testid="distance"]')
                    distance_from_downtown = parse_distance_km((await downtown_el.first.inner_text()).lower()) if await downtown_el.count() else None
                    
                    beach_el = card.locator("span.fff1944c52.d4d73793a3")
                    distance_from_beach = parse_distance_km((await beach_el.first.inner_text()).lower()) if await beach_el.count() else None

                    preferred_badge = 1 if await card.locator('[data-testid="preferred-badge"]').count() else 0
                    deal_badge = 1 if await card.locator('[data-testid="property-card-deal"]').count() else 0

                    price_el_container = card.locator('[data-testid="price-and-discounted-price"]')
                    full_price_text = await price_el_container.inner_text() if await price_el_container.count() else ""
                    extracted_discounted_value, extracted_discounted_currency = extract_price_components(full_price_text)
                    discounted_price_value = extracted_discounted_value
                    discounted_price_currency = extracted_discounted_currency

                    original_price_el_explicit = card.locator(
                        '[data-testid="price-and-discounted-price"] span[style*="line-through"], '
                        '[data-testid="price-and-discounted-price"] span.prco-old-price, '
                        '[data-testid="price-and-discounted-price"] span.e2e-original-price'
                    )
                    original_price_text = (await original_price_el_explicit.inner_text()).strip() if await original_price_el_explicit.count() else ""
                    extracted_original_value, extracted_original_currency = extract_price_components(original_price_text)
                    original_price_value = extracted_original_value
                    original_price_currency = extracted_original_currency
                    if original_price_value is None and discounted_price_value is not None:
                        original_price_value = discounted_price_value
                        original_price_currency = discounted_price_currency

                    tax_el = card.locator('[data-testid="taxes-and-charges"]')
                    taxes_and_fees_text = (await tax_el.inner_text()).strip() if await tax_el.count() else ""
                    extracted_taxes_value, extracted_taxes_currency = extract_price_components(taxes_and_fees_text)
                    taxes_value = extracted_taxes_value
                    taxes_currency = extracted_taxes_currency

                    room_type_el = card.locator('h4[role="link"]')
                    room_type = (await room_type_el.inner_text()).strip() if await room_type_el.count() else ""

                    bed_details_el = card.locator("ul.d1e8dce286 li:first-child div.fff1944c52")
                    bed_details = (await bed_details_el.inner_text()).strip() if await bed_details_el.count() else ""

                    cancellation_el = card.locator('[data-testid="cancellation-policy-icon"] + div div.fff1944c52')
                    cancellation_policy = (await cancellation_el.inner_text()).strip() if await cancellation_el.count() else ""

                    prepayment_el = card.locator('[data-testid="prepayment-policy-icon"] + div div.fff1944c52')
                    prepayment_policy = (await prepayment_el.inner_text()).strip() if await prepayment_el.count() else ""

                    availability_el = card.locator("ul.d1e8dce286 li:last-child div.b7d3eb6716")
                    availability_message = (await availability_el.inner_text()).strip() if await availability_el.count() else ""

                    nights_and_guests_el = card.locator('[data-testid="price-for-x-nights"]')
                    nights_and_guests = (await nights_and_guests_el.inner_text()).strip() if await nights_and_guests_el.count() else ""


                    target_property_listing = PropertyListing(
                        name=name,
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
                        original_price_value=original_price_value,  # Now only value
                        original_price_currency=original_price_currency,
                        discounted_price_value=discounted_price_value,
                        discounted_price_currency=discounted_price_currency,
                        taxes_and_fees_value=taxes_value,
                        taxes_and_fees_currency=taxes_currency,
                    )
                    
                    # Scrape detailed data for this specific hotel
                    target_hotel_details = await scrape_hotel_data(page, link)
                    return target_property_listing, target_hotel_details
                except Exception as e:
                    logger.error(f"Error scraping details for specific hotel '{target_hotel_name}': {e}")
                    return None, None
    
    logger.warning(f"Specific hotel '{target_hotel_name}' not found on the first page of search results.")
    return None, None