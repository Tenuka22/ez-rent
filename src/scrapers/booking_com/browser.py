import asyncio
from typing import List, Optional

from playwright.async_api import Page
from returns.result import Failure, Result, Success

from src.core.data_models import HotelDetailData, ScrapedData
from src.utils.logger import logger


async def modal_dismisser(page: Page) -> Result[None, str]:
    """
    Dismisses sign-in popups and waits for any modal to disappear.

    Args:
        page: Playwright page object.

    Returns:
        Result[None, str]: Success(None) if modals are dismissed or disappear, Failure with an error message otherwise.
    """
    try:
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
            pass # Modal might not appear, or disappear after a while.

        return Success(None)
    except Exception as e:
        logger.error(f"Error dismissing modal: {e}", exc_info=True)
        return Failure(str(e))


async def scroll_page_fully(page: Page, max_scrolls: int = 20) -> Result[None, str]:
    """
    Scroll the page multiple times until no new content loads

    Args:
        page: Playwright page object
        max_scrolls: Maximum number of scroll attempts

    Returns:
        Result[None, str]: Success(None) if scrolling completes, Failure with an error message otherwise.
    """
    try:
        logger.info("Starting full page scroll to load all content...")

        previous_height = 0
        scroll_count = 0

        while scroll_count < max_scrolls:
            # Get current scroll height
            current_height = await page.evaluate("document.body.scrollHeight")

            # If height hasn't changed, we've reached the bottom
            if current_height == previous_height:
                logger.info(f"No new content loaded after {scroll_count} scrolls")
                break

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)  # Wait for lazy-loaded content

            # Scroll to middle to trigger any lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)

            previous_height = current_height
            scroll_count += 1
            logger.info(
                f"Scroll {scroll_count}/{max_scrolls} - Height: {current_height}"
            )

        # Final scroll to top to ensure all data is accessible
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)
        logger.info("Completed full page scroll")
        return Success(None)
    except Exception as e:
        logger.error(f"Error during page scroll: {e}", exc_info=True)
        return Failure(str(e))


async def extract_facility_group(
    page: Page, group_name: str
) -> Result[Optional[List[str]], str]:
    """Extract facilities from a specific facility group"""
    facilities = []
    try:
        # Find the group by heading text
        group_selector = (
            f'[data-testid="facility-group-container"]:has(h3:has-text("{group_name}"))'
        )
        group = page.locator(group_selector).first

        if await group.count() > 0:
            # Get all facility items in this group
            items = await group.locator("li .f6b6d2a959").all()
            for item in items:
                text = await item.inner_text()
                if text:
                    facilities.append(text.strip())
        return Success(facilities if facilities else None)
    except Exception as e:
        logger.debug(f"Could not extract {group_name}: {e}")
        return Failure(str(e))


async def scrape_hotel_data(page: Page, url: str) -> Result[HotelDetailData, str]:
    """
    Scrape detailed information from a single hotel page.

    Args:
        page: Playwright page object
        url: URL of the hotel detail page

    Returns:
        Result[HotelDetailData, str]: A Success containing HotelDetailData object or a Failure with an error message if scraping fails
    """
    dismiss_result = await modal_dismisser(page)
    if isinstance(dismiss_result, Failure):
        return Failure(f"Failed to dismiss modal: {dismiss_result.failure()}")

    try:
        logger.info(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=60000)

        # Scroll to load all lazy content
        scroll_result = await scroll_page_fully(page)
        if isinstance(scroll_result, Failure):
            return Failure(f"Failed to scroll page fully: {scroll_result.failure()}")

        # ===== BASIC INFORMATION =====
        logger.info("Extracting basic information...")

        # Hotel name
        name_elem = page.locator("h2.d2fee87262").first
        name = await name_elem.inner_text() if await name_elem.count() > 0 else None

        # Star rating
        star_elem = page.locator('[data-testid="rating-stars"]').first
        star_rating = (
            await star_elem.get_attribute("aria-label")
            if await star_elem.count() > 0
            else None
        )

        # Guest rating
        rating_elem = page.locator(
            '[data-testid="review-score-right-component"] .f63b14ab7a.dff2e52086'
        ).first
        guest_rating = (
            await rating_elem.inner_text() if await rating_elem.count() > 0 else None
        )

        # Review score text (e.g., "Wonderful")
        score_text_elem = page.locator(
            '[data-testid="review-score-right-component"] .f63b14ab7a.f546354b44'
        ).first
        review_score_text = (
            await score_text_elem.inner_text()
            if await score_text_elem.count() > 0
            else None
        )

        # Review count
        review_elem = page.locator(
            '[data-testid="review-score-right-component"] .fff1944c52'
        ).first
        review_count = (
            await review_elem.inner_text() if await review_elem.count() > 0 else None
        )

        # ===== LOCATION =====
        logger.info("Extracting location information...")

        # Address
        address_elem = page.locator(".b99b6ef58f.cb4b7a25d9.b06461926f").first
        address = (
            await address_elem.inner_text() if await address_elem.count() > 0 else None
        )

        # Coordinates from map link
        coordinates = None
        map_link = page.locator("a[data-atlas-latlng]").first
        if await map_link.count() > 0:
            latlng = await map_link.get_attribute("data-atlas-latlng")
            if latlng:
                try:
                    lat, lng = latlng.split(",")
                    coordinates = {"lat": float(lat), "lng": float(lng)}
                except:
                    pass

        # Location score
        location_score_elem = page.locator(
            '[data-testid="property-description-location-score-trans"] b'
        ).first
        location_score = (
            await location_score_elem.inner_text()
            if await location_score_elem.count() > 0
            else None
        )

        # ===== DESCRIPTION =====
        logger.info("Extracting description...")

        description_elem = page.locator('[data-testid="property-description"]').first
        description = (
            await description_elem.inner_text()
            if await description_elem.count() > 0
            else None
        )

        # ===== MOST POPULAR FACILITIES =====
        logger.info("Extracting popular facilities...")

        most_popular = []
        popular_items = await page.locator(
            '[data-testid="property-most-popular-facilities-wrapper"] .f6b6d2a959'
        ).all()
        for item in popular_items:
            text = await item.inner_text()
            if text:
                most_popular.append(text.strip())

        # ===== FACILITY GROUPS =====
        logger.info("Extracting facility groups...")

        bathroom_facilities_result = await extract_facility_group(page, "Bathroom")
        if isinstance(bathroom_facilities_result, Failure):
            return Failure(
                f"Failed to extract bathroom facilities: {bathroom_facilities_result.failure()}"
            )
        bathroom_facilities = bathroom_facilities_result.unwrap()

        view_type_result = await extract_facility_group(page, "View")
        if isinstance(view_type_result, Failure):
            return Failure(
                f"Failed to extract view type: {view_type_result.failure()}"
            )
        view_type = view_type_result.unwrap()

        outdoor_facilities_result = await extract_facility_group(page, "Outdoors")
        if isinstance(outdoor_facilities_result, Failure):
            return Failure(
                f"Failed to extract outdoor facilities: {outdoor_facilities_result.failure()}"
            )
        outdoor_facilities = outdoor_facilities_result.unwrap()

        kitchen_facilities_result = await extract_facility_group(page, "Kitchen")
        if isinstance(kitchen_facilities_result, Failure):
            return Failure(
                f"Failed to extract kitchen facilities: {kitchen_facilities_result.failure()}"
            )
        kitchen_facilities = kitchen_facilities_result.unwrap()

        room_amenities_result = await extract_facility_group(page, "Room Amenities")
        if isinstance(room_amenities_result, Failure):
            return Failure(
                f"Failed to extract room amenities: {room_amenities_result.failure()}"
            )
        room_amenities = room_amenities_result.unwrap()

        activities_result = await extract_facility_group(page, "Activities")
        if isinstance(activities_result, Failure):
            return Failure(
                f"Failed to extract activities: {activities_result.failure()}"
            )
        activities = activities_result.unwrap()

        food_drink_result = await extract_facility_group(page, "Food & Drink")
        if isinstance(food_drink_result, Failure):
            return Failure(
                f"Failed to extract food & drink: {food_drink_result.failure()}"
            )
        food_drink = food_drink_result.unwrap()

        services_result = await extract_facility_group(page, "Services")
        if isinstance(services_result, Failure):
            return Failure(
                f"Failed to extract services: {services_result.failure()}"
            )
        services = services_result.unwrap()

        safety_security_result = await extract_facility_group(page, "Safety & security")
        if isinstance(safety_security_result, Failure):
            return Failure(
                f"Failed to extract safety & security: {safety_security_result.failure()}"
            )
        safety_security = safety_security_result.unwrap()

        general_facilities_result = await extract_facility_group(page, "General")
        if isinstance(general_facilities_result, Failure):
            return Failure(
                f"Failed to extract general facilities: {general_facilities_result.failure()}"
            )
        general_facilities = general_facilities_result.unwrap()

        spa_wellness_result = await extract_facility_group(page, "Spa")
        if isinstance(spa_wellness_result, Failure):
            return Failure(
                f"Failed to extract spa & wellness: {spa_wellness_result.failure()}"
            )
        spa_wellness = spa_wellness_result.unwrap()

        # ===== INTERNET & PARKING =====
        logger.info("Extracting internet and parking info...")

        # Internet info
        internet_elem = page.locator(
            '[data-testid="facility-group-container"]:has(h3:has-text("Internet")) .b99b6ef58f.fb14de7f14'
        ).first
        internet_info = (
            await internet_elem.inner_text()
            if await internet_elem.count() > 0
            else None
        )

        # Parking info
        parking_elem = page.locator(
            '[data-testid="facility-group-container"]:has(h3:has-text("Parking")) .b99b6ef58f.fb14de7f14'
        ).first
        parking_info = (
            await parking_elem.inner_text() if await parking_elem.count() > 0 else None
        )

        # ===== POOL INFORMATION =====
        logger.info("Extracting pool information...")

        pool_info = None
        pool_group = page.locator(
            '[data-testid="facility-group-container"]:has(h3:has-text("swimming pool"))'
        ).first
        if await pool_group.count() > 0:
            pool_details = []
            pool_items = await pool_group.locator("li .f6b6d2a959").all()
            for item in pool_items:
                text = await item.inner_text()
                if text:
                    pool_details.append(text.strip())

            if pool_details:
                pool_info = {
                    "type": "Outdoor swimming pool",
                    "details": pool_details,
                    "free": True,  # Based on the "Free!" indicator
                }

        # ===== LANGUAGES SPOKEN =====
        logger.info("Extracting languages...")

        languages = await extract_facility_group(page, "Languages Spoken")

        # ===== ROOM TYPES =====
        logger.info("Extracting room types...")

        room_types = []
        room_elems = await page.locator(
            '[data-testid="recommended-units"] h3, .hprt-roomtype-icon-link'
        ).all()
        for elem in room_elems[:10]:
            try:
                text = await elem.inner_text()
                if text:
                    room_types.append(text.strip())
            except:
                continue

        # ===== PRICING =====
        logger.info("Extracting pricing...")

        price_elem = page.locator('[data-testid="price-and-discounted-price"]').first
        price = await price_elem.inner_text() if await price_elem.count() > 0 else None

        # ===== CHECK-IN/CHECK-OUT =====
        logger.info("Extracting check-in/check-out times...")

        # Check-in time
        checkin_elem = (
            page.locator('div.db29ecfbe2:has-text("Check-in")')
            .locator("xpath=following-sibling::div")
            .first
        )
        check_in_time = (
            await checkin_elem.inner_text() if await checkin_elem.count() > 0 else None
        )

        # Check-out time
        checkout_elem = (
            page.locator('div.db29ecfbe2:has-text("Check-out")')
            .locator("xpath=following-sibling::div")
            .first
        )
        check_out_time = (
            await checkout_elem.inner_text()
            if await checkout_elem.count() > 0
            else None
        )

        # ===== PHOTOS COUNT =====
        logger.info("Extracting photos count...")

        photos_elem = page.locator('[data-testid="gallery-image-count"]').first
        photos_count = (
            await photos_elem.inner_text() if await photos_elem.count() > 0 else None
        )

        # ===== PROPERTY HIGHLIGHTS =====
        logger.info("Extracting property highlights...")

        highlights = []
        highlight_elems = await page.locator(
            '[data-testid="property-highlights"] div.e6208ee469, [data-testid="property-highlights"] li'
        ).all()
        for elem in highlight_elems[:15]:
            try:
                text = await elem.inner_text()
                if text:
                    highlights.append(text.strip())
            except:
                continue

        # ===== CREATE DATA OBJECT =====
        hotel_data = HotelDetailData(
            url=url,
            name=name,
            star_rating=star_rating,
            guest_rating=guest_rating,
            review_count=review_count,
            review_score_text=review_score_text,
            address=address,
            coordinates=coordinates,
            location_score=location_score,
            description=description,
            most_popular_facilities=most_popular if most_popular else None,
            bathroom_facilities=bathroom_facilities,
            view_type=view_type,
            outdoor_facilities=outdoor_facilities,
            kitchen_facilities=kitchen_facilities,
            room_amenities=room_amenities,
            activities=activities,
            food_drink=food_drink,
            internet_info=internet_info,
            parking_info=parking_info,
            services=services,
            safety_security=safety_security,
            general_facilities=general_facilities,
            pool_info=pool_info,
            spa_wellness=spa_wellness,
            languages_spoken=languages,
            room_types=room_types if room_types else None,
            price=price,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            photos_count=photos_count,
            property_highlights=highlights if highlights else None,
        )

        logger.info(f"✓ Successfully scraped: {name}")
        return Success(hotel_data)

    except Exception as e:
        logger.error(f"✗ Error scraping {url}: {e}", exc_info=True)
        return Failure(str(e))


async def scrape_properties_data(
    page: Page, limit: int
) -> Result[List[ScrapedData], str]:
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

                    star_rating_elem = card.locator(
                        'div.ebc566407a[tabindex="0"]'
                    ).first
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

                    distance_from_downtown_elem = card.locator(
                        '[data-testid="distance"]'
                    ).first
                    distance_from_downtown = (
                        await distance_from_downtown_elem.inner_text()
                        if await distance_from_downtown_elem.count() > 0
                        else None
                    )

                    distance_from_beach_elem = card.locator(
                        "span.fff1944c52.d4d73793a3"
                    ).first
                    distance_from_beach = (
                        await distance_from_beach_elem.inner_text()
                        if await distance_from_beach_elem.count() > 0
                        and "from beach" in await distance_from_beach_elem.inner_text()
                        else None
                    )

                    preferred_badge = (
                        "True"
                        if await card.locator('[data-testid="preferred-badge"]').count()
                        > 0
                        else None
                    )

                    deal_badge_elem = card.locator(
                        '[data-testid="property-card-deal"]'
                    ).first
                    deal_badge = (
                        await deal_badge_elem.inner_text()
                        if await deal_badge_elem.count() > 0
                        else None
                    )

                    room_type_elem = card.locator(
                        'div.dc7b6a60a4 h4[role="link"]'
                    ).first
                    room_type = (
                        await room_type_elem.inner_text()
                        if await room_type_elem.count() > 0
                        else None
                    )

                    bed_details_elem = card.locator(
                        "div.ba43cae375 div.fff1944c52"
                    ).first
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

                    availability_message_elem = card.locator("div.b7d3eb6716").first
                    availability_message = (
                        await availability_message_elem.inner_text()
                        if await availability_message_elem.count() > 0
                        else None
                    )

                    stay_dates_elem = card.locator(
                        'div[data-testid="flexible-dates"] span.f323fd7e96'
                    ).first
                    stay_dates = (
                        await stay_dates_elem.inner_text()
                        if await stay_dates_elem.count() > 0
                        else None
                    )

                    nights_and_guests_elem = card.locator(
                        'div[data-testid="price-for-x-nights"]'
                    ).first
                    nights_and_guests = (
                        await nights_and_guests_elem.inner_text()
                        if await nights_and_guests_elem.count() > 0
                        else None
                    )

                    original_price_elem = card.locator(
                        "span.d68334ea31.ab607752a2"
                    ).first
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

                    taxes_and_fees_elem = card.locator(
                        'div[data-testid="taxes-and-charges"]'
                    ).first
                    taxes_and_fees = (
                        await taxes_and_fees_elem.inner_text()
                        if await taxes_and_fees_elem.count() > 0
                        else None
                    )

                    hotel_data = ScrapedData(
                        name=name,
                        link=None,  # The 'link' attribute of ScrapedData is not used, so set to None.
                        hotel_link=link,  # Assign the extracted link to hotel_link.
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
