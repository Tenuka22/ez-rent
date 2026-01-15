import difflib  # Import difflib for fuzzy matching
import re
from typing import Optional

from playwright.async_api import Page

from app.data_models import HotelDetails, PropertyListing
from app.scrapers.booking_com.extractors.hotel_details_extractor import (
    scrape_hotel_data,
)
from app.scrapers.booking_com.extractors.properties_extractor import (
    _extract_property_listing_from_card,
) # Import the new helper function
from app.scrapers.booking_com.navigation import goto_properties_page
from app.scrapers.booking_com.parsers.data_parsers import (
    extract_float_value,
    extract_price_components,
    parse_distance_km,
)
from app.scrapers.booking_com.playwright_urls import BookingComUrls
from app.scrapers.booking_com.utils import modal_dismisser
from app.utils.logger import logger


async def scrape_specific_property_data(
    page: Page,
    destination: str,
    adults: int,
    rooms: int,
    target_hotel_name: str,
) -> tuple[Optional[PropertyListing], Optional[HotelDetails]]:
    """
    Navigates to the search results page, finds a specific hotel by name (or best match),
    scrapes its PropertyListing and HotelDetails.
    """
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

    # Check the first N cards for the best match
    # Limiting to 5 cards for a reasonable balance between accuracy and performance
    num_cards_to_check = min(count, 5)
    logger.info(f"Checking first {num_cards_to_check} property cards for best match.")

    for i in range(num_cards_to_check):
        card = cards.nth(i)
        name_elem = card.locator('[data-testid="title"]')
        if await name_elem.count() > 0:
            name = (await name_elem.inner_text()).strip()

            # Calculate similarity score
            # Using SequenceMatcher for fuzzy matching
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

    # Define a threshold for what constitutes a "good enough" match
    # A score of 0.8 is generally considered a strong match for names
    SIMILARITY_THRESHOLD = 0.5 # Kept at 0.5 from previous step

    if best_match_card and best_match_score >= SIMILARITY_THRESHOLD:
        logger.info(
            f"Found best matching hotel '{best_match_name}' with similarity score {best_match_score:.2f}."
        )
        try:
            target_property_listing = await _extract_property_listing_from_card(best_match_card)
            # Scrape detailed data for this specific hotel
            if target_property_listing and target_property_listing.hotel_link:
                target_hotel_details = await scrape_hotel_data(page, target_property_listing.hotel_link)
            else:
                logger.warning(
                    f"No valid property listing or link found for best match '{best_match_name}'. Skipping detailed scrape."
                )
                return None, None
            
            return target_property_listing, target_hotel_details
        except Exception as e:
            logger.error(
                f"Error scraping details for specific hotel '{best_match_name}': {e}"
            )
            return None, None
    else:
        logger.warning(
            f"Specific hotel '{target_hotel_name}' not found or no sufficiently close match on the first page of search results."
        )
        return None, None
