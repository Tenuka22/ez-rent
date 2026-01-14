import asyncio
import re
from typing import List, Optional

from playwright.async_api import Page


from app.data_models import HotelDetails, PropertyListing
from app.utils.logger import logger


def extract_price_components(
    price_string: str | None,
) -> tuple[float | None, str | None]:
    logger.debug(f"extract_price_components: Input price_string: {price_string}")
    if not isinstance(price_string, str):
        logger.debug("extract_price_components: Input is not a string, returning None, None.")
        return None, None

    # Normalize spaces (e.g., non-breaking space)
    price_string = price_string.replace("\u202f", " ").strip()

    # Regex to capture potential currency and the main number part.
    currency_pattern = r"[€$£¥₹₽]|LKR|USD|EUR|GBP|AUD|CAD|CHF|CNY|SEK|NZD|MXN|SGD|HKD|NOK|KRW|TRY|RUB|INR|BRL|ZAR|Rs\.?"
    number_pattern = r"\d{1,3}(?:[.,\s]?\d{3})*(?:[.,]\d{1,2})?"

    full_pattern = (
        rf"({currency_pattern})?\s*({number_pattern})\s*({currency_pattern})?"
    )
    match = re.search(full_pattern, price_string, re.IGNORECASE)

    if not match:
        num_only_match = re.search(number_pattern, price_string)
        if not num_only_match:
            logger.debug("extract_price_components: No number found, returning None, None.")
            return None, None
        found_number_str = num_only_match.group(0)
        currency_symbol = None
        logger.debug(f"extract_price_components: No currency match, found_number_str: {found_number_str}")
    else:
        currency_symbol_found = match.group(1) or match.group(3)
        currency_symbol = (
            currency_symbol_found.upper() if currency_symbol_found else None
        )
        # Normalize Rs to LKR
        if currency_symbol and currency_symbol.startswith("RS"):
            currency_symbol = "LKR"
        found_number_str = match.group(2)
        logger.debug(f"extract_price_components: Matched currency: {currency_symbol}, found_number_str: {found_number_str}")


    if not found_number_str:
        logger.debug("extract_price_components: found_number_str is empty, returning None, currency_symbol.")
        return None, currency_symbol

    # Clean the number string
    cleaned_number_str = found_number_str.replace(" ", "")
    logger.debug(f"extract_price_components: cleaned_number_str: {cleaned_number_str}")

    # Determine decimal and thousands separators
    last_dot_idx = cleaned_number_str.rfind(".")
    last_comma_idx = cleaned_number_str.rfind(",")

    if last_dot_idx == -1 and last_comma_idx == -1:
        processed_number = cleaned_number_str
    elif last_dot_idx != -1 and last_comma_idx != -1:
        if last_comma_idx > last_dot_idx:
            processed_number = cleaned_number_str.replace(".", "").replace(",", ".")
        else:
            processed_number = cleaned_number_str.replace(",", "")
    elif last_dot_idx != -1:
        if len(cleaned_number_str) - 1 - last_dot_idx <= 2:
            processed_number = cleaned_number_str
        else:
            processed_number = cleaned_number_str.replace(".", "")
    else:
        if len(cleaned_number_str) - 1 - last_comma_idx <= 2:
            processed_number = cleaned_number_str.replace(",", ".")
        else:
            processed_number = cleaned_number_str.replace(",", "")
    logger.debug(f"extract_price_components: processed_number before float conversion: {processed_number}")

    try:
        result_value = float(processed_number)
        logger.debug(f"extract_price_components: Successfully parsed value: {result_value}, currency: {currency_symbol}")
        return result_value, currency_symbol
    except ValueError:
        logger.debug(f"extract_price_components: ValueError for {processed_number}, returning None, currency_symbol.")
        return None, currency_symbol


def extract_float_value(value_string: str | None) -> float | None:
    logger.debug(f"extract_float_value: Input value_string: {value_string}")
    if not isinstance(value_string, str):
        logger.debug("extract_float_value: Input is not a string, returning None.")
        return None

    value_string = value_string.replace("\u202f", " ").strip()
    match = re.search(r"(\d{1,3}(?:[.,\s]?\d{3})*(?:[.,]\d{1,2})?)", value_string)
    if not match:
        logger.debug("extract_float_value: No number found in string, returning None.")
        return None

    found_number_str = match.group(1)
    if not found_number_str:
        logger.debug("extract_float_value: found_number_str is empty after match, returning None.")
        return None
    logger.debug(f"extract_float_value: found_number_str: {found_number_str}")

    cleaned_number_str = found_number_str.replace(" ", "")
    logger.debug(f"extract_float_value: cleaned_number_str: {cleaned_number_str}")
    last_dot_idx = cleaned_number_str.rfind(".")
    last_comma_idx = cleaned_number_str.rfind(",")

    if last_dot_idx == -1 and last_comma_idx == -1:
        processed_number = cleaned_number_str
    elif last_dot_idx != -1 and last_comma_idx != -1:
        if last_comma_idx > last_dot_idx:
            processed_number = cleaned_number_str.replace(".", "").replace(",", ".")
        else:
            processed_number = cleaned_number_str.replace(",", "")
    elif last_dot_idx != -1:
        if len(cleaned_number_str) - 1 - last_dot_idx <= 2:
            processed_number = cleaned_number_str
        else:
            processed_number = cleaned_number_str.replace(".", "")
    else:
        if len(cleaned_number_str) - 1 - last_comma_idx <= 2:
            processed_number = cleaned_number_str.replace(",", ".")
        else:
            processed_number = cleaned_number_str.replace(",", "")
    logger.debug(f"extract_float_value: processed_number before float conversion: {processed_number}")

    try:
        result_value = float(processed_number)
        logger.debug(f"extract_float_value: Successfully parsed value: {result_value}")
        return result_value
    except ValueError:
        logger.debug(f"extract_float_value: ValueError for {processed_number}, returning None.")
        return None


async def modal_dismisser(page: Page) -> None:
    """Dismisses sign-in popups and waits for any modal to disappear."""
    logger.info("Attempting to dismiss any visible modals...")
    dismiss_selectors = [
        'button[aria-label="Dismiss sign-in info."]',
        "button.de576f5064.b46cd7aad7.e26a59bb37",
        'div.a5c71b0007 button[type="button"]',
        'button[aria-label="Close"]',
        'button:has-text("Close")',
    ]
    for selector in dismiss_selectors:
        logger.debug(f"Trying selector: {selector}")
        try:
            dismiss = page.locator(selector).first
            if await dismiss.is_visible(timeout=1000): # Reduced timeout to quickly check visibility
                logger.info(f"Dismissing modal with selector: {selector}")
                await dismiss.scroll_into_view_if_needed()
                await dismiss.click(force=True)
                await asyncio.sleep(0.5)
                break
        except Exception: # Catch specific exceptions if known, otherwise general
            logger.debug(f"Selector {selector} did not find a visible modal or failed to click.")
            continue

    # Wait for any modal to disappear
    modal = page.locator("div.a5c71b0007")
    try:
        logger.debug("Waiting for modal to disappear...")
        await modal.wait_for(state="hidden", timeout=3000)
        logger.info("Modal successfully disappeared.")
    except Exception:
        logger.debug("No modal detected or modal did not disappear within timeout.")
        return


async def scroll_page_fully(page: Page, max_scrolls: int = 25) -> None:
    """Scroll the page multiple times until no new content loads"""
    try:
        logger.info("Starting full page scroll to load all content...")

        previous_height = 0
        scroll_count = 0
        no_change_count = 0

        while scroll_count < max_scrolls:
            current_height = await page.evaluate("document.body.scrollHeight")

            if current_height == previous_height:
                no_change_count += 1
                if no_change_count >= 3:
                    logger.info(f"No new content loaded after {scroll_count} scrolls")
                    break
            else:
                no_change_count = 0

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Scroll to middle
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)

            previous_height = current_height
            scroll_count += 1
            logger.info(
                f"Scroll {scroll_count}/{max_scrolls} - Height: {current_height}"
            )

        # Final scroll to top
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)
        logger.info("Completed full page scroll")
        return
    except Exception as e:
        logger.error(f"Error during page scroll: {e}", exc_info=True)
        raise


async def extract_facility_group(
    page: Page, group_name: str
) -> Optional[List[str]]:
    """Extract facilities from a specific facility group"""
    logger.info(f"Attempting to extract facility group: {group_name}")
    facilities = []
    try:
        group_selector = (
            f'[data-testid="facility-group-container"]:has(h3:has-text("{group_name}"))'
        )
        group = page.locator(group_selector).first

        if await group.count() > 0:
            items = await group.locator("li .f6b6d2a959").all()
            logger.debug(f"Found {len(items)} items in facility group '{group_name}'")
            for item in items:
                text = await item.inner_text()
                if text:
                    facilities.append(text.strip())
                    logger.debug(f"Extracted facility: {text.strip()}")
        if facilities:
            logger.info(f"Successfully extracted {len(facilities)} facilities for group: {group_name}")
        else:
            logger.info(f"No facilities found for group: {group_name}")
        return facilities if facilities else None
    except Exception as e:
        logger.debug(f"Could not extract {group_name}: {e}")
        return None


async def scrape_hotel_data(page: Page, url: str) -> HotelDetails:
    """Scrape detailed information from a single hotel page."""
    try:
        logger.info(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=60000)

        # Dismiss modal first
        await modal_dismisser(page)
        await asyncio.sleep(1)

        # Scroll to load all lazy content
        await scroll_page_fully(page)

        # ===== BASIC INFORMATION =====
        logger.info("Extracting basic information...")

        # Try multiple selectors for hotel name
        name = None
        name_selectors = [
            "h2.d2fee87262",
            "h2.pp-header__title",
            '[data-testid="title"]',
            "h1",
            "h2",
        ]
        for selector in name_selectors:
            try:
                name_elem = page.locator(selector).first
                if await name_elem.count() > 0:
                    name = await name_elem.inner_text()
                    if name and len(name.strip()) > 0:
                        name = name.strip()
                        break
            except:
                continue

        if not name:
            logger.error(f"Hotel name could not be extracted for URL: {url}")
            raise Exception(f"Hotel name could not be extracted for URL: {url}")

        # Star rating
        star_rating = None
        star_selectors = [
            '[data-testid="rating-stars"]',
            ".bui-rating__stars",
            '[aria-label*="star"]',
        ]
        for selector in star_selectors:
            try:
                star_elem = page.locator(selector).first
                if await star_elem.count() > 0:
                    star_rating = await star_elem.get_attribute("aria-label")
                    if star_rating:
                        break
            except:
                continue

        # Guest rating
        guest_rating = None
        rating_selectors = [
            '[data-testid="review-score-right-component"] .f63b14ab7a.dff2e52086',
            ".bui-review-score__badge",
            '[data-testid="review-score-badge"]',
        ]
        for selector in rating_selectors:
            try:
                rating_elem = page.locator(selector).first
                if await rating_elem.count() > 0:
                    guest_rating = await rating_elem.inner_text()
                    if guest_rating:
                        break
            except:
                continue

        # Review score text
        review_score_text = None
        score_text_selectors = [
            '[data-testid="review-score-right-component"] .f63b14ab7a.f546354b44',
            ".bui-review-score__text",
        ]
        for selector in score_text_selectors:
            try:
                score_text_elem = page.locator(selector).first
                if await score_text_elem.count() > 0:
                    review_score_text = await score_text_elem.inner_text()
                    if review_score_text:
                        break
            except:
                continue

        # Review count
        review_count = None
        review_selectors = [
            '[data-testid="review-score-right-component"] .fff1944c52',
            ".bui-review-score__review-count",
        ]
        for selector in review_selectors:
            try:
                review_elem = page.locator(selector).first
                if await review_elem.count() > 0:
                    review_count = await review_elem.inner_text()
                    if review_count:
                        break
            except:
                continue

        # ===== LOCATION =====
        logger.info("Extracting location information...")

        address = None
        address_selectors = [
            ".b99b6ef58f.cb4b7a25d9.b06461926f",
            '[data-testid="address"]',
            ".hp_address_subtitle",
        ]
        for selector in address_selectors:
            try:
                address_elem = page.locator(selector).first
                if await address_elem.count() > 0:
                    address = await address_elem.inner_text()
                    if address:
                        break
            except:
                continue

        # Coordinates
        coordinates = None
        map_selectors = [
            "a[data-atlas-latlng]",
            'a[href*="maps"]',
        ]
        for selector in map_selectors:
            try:
                map_link = page.locator(selector).first
                if await map_link.count() > 0:
                    latlng = await map_link.get_attribute("data-atlas-latlng")
                    if latlng and "," in latlng:
                        lat, lng = latlng.split(",")
                        coordinates = {
                            "lat": float(lat.strip()),
                            "lng": float(lng.strip()),
                        }
                        break
            except:
                continue

        # Location score
        location_score = None
        location_score_selectors = [
            '[data-testid="property-description-location-score-trans"] b',
            ".hp_location_score b",
        ]
        for selector in location_score_selectors:
            try:
                location_score_elem = page.locator(selector).first
                if await location_score_elem.count() > 0:
                    location_score = await location_score_elem.inner_text()
                    if location_score:
                        break
            except:
                continue

        # ===== DESCRIPTION =====
        logger.info("Extracting description...")

        description = None
        description_selectors = [
            '[data-testid="property-description"]',
            "#property_description_content",
        ]
        for selector in description_selectors:
            try:
                description_elem = page.locator(selector).first
                if await description_elem.count() > 0:
                    description = await description_elem.inner_text()
                    if description:
                        break
            except:
                continue

        # ===== MOST POPULAR FACILITIES =====
        logger.info("Extracting popular facilities...")

        most_popular = []
        popular_selectors = [
            '[data-testid="property-most-popular-facilities-wrapper"] .f6b6d2a959',
            ".hotel-facilities .facility",
        ]
        for selector in popular_selectors:
            try:
                popular_items = await page.locator(selector).all()
                for item in popular_items:
                    text = await item.inner_text()
                    if text:
                        most_popular.append(text.strip())
                if most_popular:
                    break
            except:
                continue

        # ===== FACILITY GROUPS =====
        logger.info("Extracting facility groups...")

        bathroom_facilities = await extract_facility_group(page, "Bathroom")
        view_type = await extract_facility_group(page, "View")
        outdoor_facilities = await extract_facility_group(page, "Outdoors")
        kitchen_facilities = await extract_facility_group(page, "Kitchen")
        room_amenities = await extract_facility_group(page, "Room Amenities")
        activities = await extract_facility_group(page, "Activities")
        food_drink = await extract_facility_group(page, "Food & Drink")
        services = await extract_facility_group(page, "Services")
        safety_security = await extract_facility_group(page, "Safety & security")
        general_facilities = await extract_facility_group(page, "General")
        spa_wellness = await extract_facility_group(page, "Spa")

        # ===== INTERNET & PARKING =====
        logger.info("Extracting internet and parking info...")

        internet_info = None
        internet_selectors = [
            '[data-testid="facility-group-container"]:has(h3:has-text("Internet")) .b99b6ef58f.fb14de7f14',
        ]
        for selector in internet_selectors:
            try:
                internet_elem = page.locator(selector).first
                if await internet_elem.count() > 0:
                    internet_info = await internet_elem.inner_text()
                    if internet_info:
                        break
            except:
                continue

        parking_info = None
        parking_selectors = [
            '[data-testid="facility-group-container"]:has(h3:has-text("Parking")) .b99b6ef58f.fb14de7f14',
        ]
        for selector in parking_selectors:
            try:
                parking_elem = page.locator(selector).first
                if await parking_elem.count() > 0:
                    parking_info = await parking_elem.inner_text()
                    if parking_info:
                        break
            except:
                continue

        # ===== POOL INFORMATION =====
        logger.info("Extracting pool information...")

        pool_info = None
        try:
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
                        "free": True,
                    }
        except:
            pass

        # ===== LANGUAGES SPOKEN =====
        logger.info("Extracting languages...")
        languages = await extract_facility_group(page, "Languages Spoken")

        # ===== ROOM TYPES =====
        logger.info("Extracting room types...")

        room_types = []
        room_selectors = [
            '[data-testid="recommended-units"] h3',
            ".hprt-roomtype-icon-link",
        ]
        for selector in room_selectors:
            try:
                room_elems = await page.locator(selector).all()
                for elem in room_elems[:10]:
                    text = await elem.inner_text()
                    if text:
                        room_types.append(text.strip())
                if room_types:
                    break
            except:
                continue

        # ===== PRICING =====
        logger.info("Extracting pricing...")

        price = None
        price_selectors = [
            '[data-testid="price-and-discounted-price"]',
            ".prco-valign-middle-helper",
            ".bui-price-display__value",
        ]
        for selector in price_selectors:
            try:
                price_elem = page.locator(selector).first
                if await price_elem.count() > 0:
                    price = await price_elem.inner_text()
                    if price:
                        break
            except:
                continue

        if not price:
            logger.warning(f"Price could not be extracted for URL: {url}")

        # ===== CHECK-IN/CHECK-OUT =====
        logger.info("Extracting check-in/check-out times...")

        check_in_time = None
        try:
            checkin_elem = (
                page.locator('div.db29ecfbe2:has-text("Check-in")')
                .locator("xpath=following-sibling::div")
                .first
            )
            if await checkin_elem.count() > 0:
                check_in_time = await checkin_elem.inner_text()
        except:
            pass

        check_out_time = None
        try:
            checkout_elem = (
                page.locator('div.db29ecfbe2:has-text("Check-out")')
                .locator("xpath=following-sibling::div")
                .first
            )
            if await checkout_elem.count() > 0:
                check_out_time = await checkout_elem.inner_text()
        except:
            pass

        # ===== PHOTOS COUNT =====
        logger.info("Extracting photos count...")

        photos_count = None
        photos_selectors = [
            '[data-testid="gallery-image-count"]',
            ".bh-photo-grid-thumb-count",
        ]
        for selector in photos_selectors:
            try:
                photos_elem = page.locator(selector).first
                if await photos_elem.count() > 0:
                    photos_count = await photos_elem.inner_text()
                    if photos_count:
                        break
            except:
                continue

        # ===== PROPERTY HIGHLIGHTS =====
        logger.info("Extracting property highlights...")

        highlights = []
        highlights_selectors = [
            '[data-testid="property-highlights"] div.e6208ee469',
            '[data-testid="property-highlights"] li',
        ]
        for selector in highlights_selectors:
            try:
                highlight_elems = await page.locator(selector).all()
                for elem in highlight_elems[:15]:
                    text = await elem.inner_text()
                    if text:
                        highlights.append(text.strip())
                if highlights:
                    break
            except:
                continue

        # ===== CREATE DATA OBJECT =====
        hotel_data = HotelDetails(
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
        return hotel_data

    except Exception as e:
        logger.error(f"✗ Error scraping {url}: {e}", exc_info=True)
        raise Exception(f"Error scraping {url}: {e}")


async def scrape_properties_data(
    page: Page, limit: int
) -> List[PropertyListing]:
    try:
        hotels: List[PropertyListing] = []
        seen_links = set()

        last_height = 0
        same_count = 0

        while True:
            await page.wait_for_load_state("networkidle")

            property_cards = await page.locator('[data-testid="property-card"]').all()
            logger.debug(f"Found {len(property_cards)} properties on current scroll")

            for idx, card in enumerate(property_cards):
                try:
                    link_elem = card.locator('a[data-testid="title-link"]').first
                    link = (
                        await link_elem.get_attribute("href")
                        if await link_elem.count() > 0
                        else None
                    )

                    if not link or link in seen_links:
                        continue
                    seen_links.add(link)

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
                    raw_star_rating = (
                        await star_rating_elem.get_attribute("aria-label")
                        if await star_rating_elem.count() > 0
                        else None
                    )
                    star_rating = extract_float_value(raw_star_rating)

                    guest_rating_score_elem = card.locator(
                        '[data-testid="review-score"] > div:first-child'
                    ).first
                    raw_guest_rating_score = (
                        await guest_rating_score_elem.inner_text()
                        if await guest_rating_score_elem.count() > 0
                        else None
                    )
                    guest_rating_score = extract_float_value(raw_guest_rating_score)

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
                    raw_distance_from_downtown = (
                        await distance_from_downtown_elem.inner_text()
                        if await distance_from_downtown_elem.count() > 0
                        else None
                    )
                    distance_from_downtown = extract_float_value(
                        raw_distance_from_downtown
                    )

                    distance_from_beach_elem = card.locator(
                        "span.fff1944c52.d4d73793a3"
                    ).first
                    distance_from_beach = None
                    if await distance_from_beach_elem.count() > 0:
                        beach_text = await distance_from_beach_elem.inner_text()
                        if beach_text and "from beach" in beach_text.lower():
                            distance_from_beach = beach_text

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
                    original_price_str = (
                        await original_price_elem.inner_text()
                        if await original_price_elem.count() > 0
                        else None
                    )
                    original_price_value, original_price_currency = (
                        extract_price_components(original_price_str)
                    )

                    discounted_price_elem = card.locator(
                        '[data-testid="price-and-discounted-price"]'
                    ).first
                    discounted_price_str = (
                        await discounted_price_elem.inner_text()
                        if await discounted_price_elem.count() > 0
                        else None
                    )
                    discounted_price_value, discounted_price_currency = (
                        extract_price_components(discounted_price_str)
                    )

                    taxes_and_fees_elem = card.locator(
                        'div[data-testid="taxes-and-charges"]'
                    ).first
                    taxes_and_fees_str = (
                        await taxes_and_fees_elem.inner_text()
                        if await taxes_and_fees_elem.count() > 0
                        else None
                    )
                    taxes_and_fees_value, taxes_and_fees_currency = (
                        extract_price_components(taxes_and_fees_str)
                    )

                    hotel_data = PropertyListing(
                        name=name,
                        link=None,
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
                        stay_dates=stay_dates,
                        nights_and_guests=nights_and_guests,
                        original_price=original_price_str,
                        original_price_value=original_price_value,
                        original_price_currency=original_price_currency,
                        discounted_price=discounted_price_str,
                        discounted_price_value=discounted_price_value,
                        discounted_price_currency=discounted_price_currency,
                        taxes_and_fees=taxes_and_fees_str,
                        taxes_and_fees_value=taxes_and_fees_value,
                        taxes_and_fees_currency=taxes_and_fees_currency,
                    )
                    hotels.append(hotel_data)
                    logger.info(f"Scraped: {name}")

                    if len(hotels) >= limit:
                        logger.info(f"Scraped {limit} properties, stopping.")
                        return hotels[:limit]

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

        return hotels

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise Exception(f"Error during scraping: {e}")
