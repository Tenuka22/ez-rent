import asyncio
from typing import List

from playwright.async_api import Page
from returns.result import Failure, Result, Success

from src.core.data_models import ScrapedData
from src.utils.logger import logger


async def modal_dismisser(page: Page):
    # Dismiss sign-in popups
    dismiss_selectors = [
        'button[aria-label="Dismiss sign-in info."]',
        "button.de576f5064.b46cd7aad7.e26a59bb37",
        'div.a5c71b0007 button[type="button"]',
    ]
    for selector in dismiss_selectors:
        dismiss = page.locator(selector).first
        if await dismiss.is_visible(timeout=2000):
            await dismiss.scroll_into_view_if_needed()
            await dismiss.click(force=True)
            break

    # Wait for any modal to disappear
    modal = page.locator("div.a5c71b0007")
    try:
        await modal.wait_for(state="hidden", timeout=3000)
    except Exception:
        pass


async def scrape_properties_data(page: Page, limit: int) -> Result[List[ScrapedData], str]:
    try:
        hotels: List[ScrapedData] = []
        seen_links = set()

        last_height = 0
        same_count = 0

        while True:
            await page.wait_for_load_state("networkidle")

            # Extract property cards
            property_cards = await page.locator('[data-testid="property-card"]').all()
            logger.debug(f"Found {len(property_cards)} properties on current scroll")

            for idx, card in enumerate(property_cards):
                try:
                    # Hotel link (for deduplication)
                    link_elem = card.locator('a[data-testid="title-link"]').first
                    link = (
                        await link_elem.get_attribute("href")
                        if await link_elem.count() > 0
                        else None
                    )

                    if not link or link in seen_links:
                        continue
                    seen_links.add(link)

                    # Hotel details
                    name_elem = card.locator('[data-testid="title"]').first
                    name = (
                        await name_elem.inner_text()
                        if await name_elem.count() > 0
                        else "N/A"
                    )

                    address_elem = card.locator('[data-testid="address"]').first
                    address = (
                        await address_elem.inner_text()
                        if await address_elem.count() > 0
                        else None
                    )

                    star_rating_elem = card.locator('div.ebc566407a[tabindex="0"]').first
                    star_rating = (
                        await star_rating_elem.get_attribute("aria-label")
                        if await star_rating_elem.count() > 0
                        else None
                    )

                    guest_rating_score_elem = card.locator(
                        '[data-testid="review-score"] > div:first-child'
                    ).first
                    guest_rating_score = (
                        await guest_rating_score_elem.inner_text()
                        if await guest_rating_score_elem.count() > 0
                        else None
                    )

                    reviews_elem = card.locator(
                        '[data-testid="review-score"] div:nth-child(2)'
                    ).first
                    reviews = (
                        await reviews_elem.inner_text()
                        if await reviews_elem.count() > 0
                        else None
                    )

                    distance_from_downtown_elem = card.locator('[data-testid="distance"]').first
                    distance_from_downtown = (
                        await distance_from_downtown_elem.inner_text()
                        if await distance_from_downtown_elem.count() > 0
                        else None
                    )

                    distance_from_beach_elem = card.locator('span.fff1944c52.d4d73793a3').first
                    distance_from_beach = (
                        await distance_from_beach_elem.inner_text()
                        if await distance_from_beach_elem.count() > 0
                        and "from beach" in await distance_from_beach_elem.inner_text()
                        else None
                    )

                    preferred_badge = (
                        "True"
                        if await card.locator('[data-testid="preferred-badge"]').count() > 0
                        else None
                    )

                    deal_badge_elem = card.locator('[data-testid="property-card-deal"]').first
                    deal_badge = (
                        await deal_badge_elem.inner_text()
                        if await deal_badge_elem.count() > 0
                        else None
                    )

                    room_type_elem = card.locator('div.dc7b6a60a4 h4[role="link"]').first
                    room_type = (
                        await room_type_elem.inner_text()
                        if await room_type_elem.count() > 0
                        else None
                    )

                    bed_details_elem = card.locator('div.ba43cae375 div.fff1944c52').first
                    bed_details = (
                        await bed_details_elem.inner_text()
                        if await bed_details_elem.count() > 0
                        else None
                    )

                    cancellation_policy_elem = card.locator(
                        'div[data-testid="cancellation-policy-icon"] ~ div.ca9d921c46 div.fff1944c52'
                    ).first
                    cancellation_policy = (
                        await cancellation_policy_elem.inner_text()
                        if await cancellation_policy_elem.count() > 0
                        else None
                    )

                    prepayment_policy_elem = card.locator(
                        'div[data-testid="prepayment-policy-icon"] ~ div.ca9d921c46 div.fff1944c52'
                    ).first
                    prepayment_policy = (
                        await prepayment_policy_elem.inner_text()
                        if await prepayment_policy_elem.count() > 0
                        else None
                    )

                    availability_message_elem = card.locator('div.b7d3eb6716').first
                    availability_message = (
                        await availability_message_elem.inner_text()
                        if await availability_message_elem.count() > 0
                        else None
                    )

                    stay_dates_elem = card.locator('div[data-testid="flexible-dates"] span.f323fd7e96').first
                    stay_dates = (
                        await stay_dates_elem.inner_text()
                        if await stay_dates_elem.count() > 0
                        else None
                    )

                    nights_and_guests_elem = card.locator('div[data-testid="price-for-x-nights"]').first
                    nights_and_guests = (
                        await nights_and_guests_elem.inner_text()
                        if await nights_and_guests_elem.count() > 0
                        else None
                    )

                    original_price_elem = card.locator('span.d68334ea31.ab607752a2').first
                    original_price = (
                        await original_price_elem.inner_text()
                        if await original_price_elem.count() > 0
                        else None
                    )

                    discounted_price_elem = card.locator(
                        '[data-testid="price-and-discounted-price"]'
                    ).first
                    discounted_price = (
                        await discounted_price_elem.inner_text()
                        if await discounted_price_elem.count() > 0
                        else None
                    )

                    taxes_and_fees_elem = card.locator('div[data-testid="taxes-and-charges"]').first
                    taxes_and_fees = (
                        await taxes_and_fees_elem.inner_text()
                        if await taxes_and_fees_elem.count() > 0
                        else None
                    )

                    hotel_data = ScrapedData(
                        name=name,
                        link=link,
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
                        stay_dates=stay_dates,
                        nights_and_guests=nights_and_guests,
                        original_price=original_price,
                        discounted_price=discounted_price,
                        taxes_and_fees=taxes_and_fees,
                    )
                    hotels.append(hotel_data)
                    logger.info(f"Scraped: {name}")

                    if len(hotels) >= limit:
                        logger.info(f"Scraped {limit} properties, stopping.")
                        return Success(hotels[:limit])

                except Exception as e:
                    logger.error(f"Error extracting hotel {idx}: {e}")
                    continue

            # Check if "Load more results" button exists
            load_more_btn = page.locator('button:has-text("Load more results")').first
            if await load_more_btn.count() > 0 and await load_more_btn.is_visible():
                logger.info("Clicking 'Load more results'...")
                await load_more_btn.click()
                await asyncio.sleep(3)  # wait for more results to load
                last_height = await page.evaluate(
                    "document.body.scrollHeight"
                )  # reset height tracking
                same_count = 0
                continue  # go back to top of loop to scrape newly loaded cards

            # Scroll to bottom if no load more button
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                same_count += 1
                if same_count >= 2:  # bottom reached
                    logger.info("Reached bottom, finished scraping.")
                    break
            else:
                same_count = 0
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                last_height = new_height

        return Success(hotels)

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return Failure(f"Error during scraping: {e}")
