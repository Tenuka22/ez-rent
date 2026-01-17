from typing import List

from playwright.async_api import Page

from app.data_models import PropertyListing
from app.scrapers.booking_com.extractors.extract_property_listing_from_card import (
    extract_property_listing_from_card,
)
from app.utils.logger import logger


async def scrape_properties_data(page: Page, limit: int) -> List[PropertyListing]:
    """
    Scrapes property listings from the current page until the limit is reached or no more properties are found.

    Args:
        page (Page): Playwright Page object.
        limit (int): The maximum number of property listings to scrape.

    Returns:
        List[PropertyListing]: A list of scraped PropertyListing objects.
    """
    hotels: List[PropertyListing] = []
    seen_links: set[str] = set()
    last_card_count = 0

    while len(hotels) < limit:
        await page.wait_for_load_state("networkidle")

        cards = page.locator('[data-testid="property-card"]')
        current_card_count = await cards.count()
        logger.info(f"Found {current_card_count} property cards")

        # Process new cards since last scroll
        for i in range(last_card_count, current_card_count):
            if len(hotels) >= limit:
                break

            card = cards.nth(i)

            try:
                property_listing = await extract_property_listing_from_card(card)

                if (
                    not property_listing.hotel_link
                    or property_listing.hotel_link in seen_links
                ):
                    continue
                seen_links.add(property_listing.hotel_link)
                hotels.append(property_listing)
                logger.info(f"✓ Listing scraped: {property_listing.name}")

            except ValueError as ve:
                logger.warning(
                    f"Failed to extract property listing from card due to: {ve}"
                )
                continue
            except Exception as e:
                logger.warning(f"Failed to parse listing card: {e}")
                continue

        last_card_count = current_card_count

        # ---------- LOAD MORE ----------
        load_more = page.locator('button:has-text("Load more results")')
        if await load_more.count() and await load_more.is_visible():
            await load_more.click()
            await page.wait_for_load_state("networkidle")
            continue

        # ---------- SCROLL AND WAIT FOR MORE CARDS ----------
        # Scroll to load more if no "Load more results" button was found or clicked
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        await page.wait_for_timeout(
            3000
        )  # Give a small moment for scroll to take effect and new content to initiate loading

        new_card_count = await cards.count()

        # If after scrolling, no new cards are found and no "Load more results" button,
        # it implies no more content is available. This prevents an infinite loop.
        if new_card_count == current_card_count and not (await load_more.count() and await load_more.is_visible()):
            logger.info(
                "No new cards appeared after scrolling and no 'Load more results' button, stopping."
            )
            break

    return hotels[:limit]
