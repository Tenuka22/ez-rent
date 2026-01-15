import difflib  # Import difflib for fuzzy matching
from typing import Optional

from playwright.async_api import Page

from app.data_models import HotelDetails, PropertyListing
from app.scrapers.booking_com.extractors.hotel_details_extractor import (
    scrape_hotel_data,
)
from app.scrapers.booking_com.extractors.properties_extractor import (
    extract_property_listing_from_card,
)
from app.scrapers.booking_com.navigation import goto_properties_page
from app.scrapers.booking_com.playwright_urls import BookingComUrls
from app.utils.logger import logger


async def scrape_specific_property_data(
    page: Page,
    adults: int,
    rooms: int,
    target_hotel_name: str,
) -> tuple[PropertyListing, HotelDetails]:
    logger.info(f"Searching for specific hotel: '{target_hotel_name}'")

    urls = BookingComUrls()
    await goto_properties_page(
        page=page,
        destination=target_hotel_name,
        urls=urls,
        adults=adults,
        rooms=rooms,
    )

    await page.wait_for_load_state("networkidle", timeout=60_000)
    await page.wait_for_selector('[data-testid="property-card"]', timeout=30_000)

    target_property_listing: Optional[PropertyListing] = None
    target_hotel_details: Optional[HotelDetails] = None

    cards = page.locator('[data-testid="property-card"]')
    count = await cards.count()

    best_match_card = None
    best_match_score = 0.0
    best_match_name = ""

    num_cards_to_check = min(count, 5)
    logger.info(f"Checking first {num_cards_to_check} property cards for best match.")

    for i in range(num_cards_to_check):
        card = cards.nth(i)
        name_elem = card.locator('[data-testid="title"]')
        if await name_elem.count() > 0:
            name = (await name_elem.inner_text()).strip()

            similarity_score = difflib.SequenceMatcher(
                None, target_hotel_name.lower(), name.lower()
            ).ratio()

            logger.debug(
                f"Comparing '{target_hotel_name}' with '{name}', score: {similarity_score:.2f}"
            )

            if similarity_score > best_match_score:
                best_match_score = similarity_score
                best_match_card = card
                best_match_name = name

    SIMILARITY_THRESHOLD = 0.5

    if best_match_card and best_match_score >= SIMILARITY_THRESHOLD:
        logger.info(
            f"Found best matching hotel '{best_match_name}' with similarity score {best_match_score:.2f}."
        )
        try:
            target_property_listing = await extract_property_listing_from_card(
                best_match_card
            )
            if target_property_listing and target_property_listing.hotel_link:
                target_hotel_details = await scrape_hotel_data(
                    page, target_property_listing.hotel_link
                )
            else:
                logger.warning(
                    f"No valid property listing or link found for best match '{best_match_name}'. Skipping detailed scrape."
                )
                return None, None

            return target_property_listing, target_hotel_details
        except Exception as e:
            raise Exception(
                f"Error scraping details for specific hotel '{best_match_name}': {e}"
            )
    else:
        raise Exception(
            f"Specific hotel '{target_hotel_name}' not found or no sufficiently close match on the first page of search results."
        )
