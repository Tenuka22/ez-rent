import asyncio
import re
from typing import List, Optional

from playwright.async_api import Page

from app.data_models import HotelDetails, PropertyListing
from app.utils.logger import logger


def extract_price_components(
    price_string: str | None,
) -> tuple[float | None, str]:  # Changed return type for currency to str
    logger.debug(f"extract_price_components: Input price_string: {price_string}")
    if not isinstance(price_string, str):
        logger.debug(
            "extract_price_components: Input is not a string, returning None, ''."
        )
        return None, ""  # Changed to empty string

    # Normalize spaces (e.g., non-breaking space)
    price_string = price_string.replace("\u202f", " ").strip()

    # Regex to capture potential currency and the main number part.
    currency_pattern = r"[€$£¥₹₽]|LKR|USD|EUR|GBP|AUD|CAD|CHF|CNY|SEK|NZD|MXN|SGD|HKD|NOK|KRW|TRY|RUB|INR|BRL|ZAR|Rs\.?"
    number_pattern = r"\d{1,3}(?:[.,\s]?\d{3})*(?:[.,]\d{1,2})?"

    full_pattern = (
        rf"({currency_pattern})?\s*({number_pattern})\s*({currency_pattern})?"
    )
    match = re.search(full_pattern, price_string, re.IGNORECASE)

    # Handle cases like "Includes taxes and charges" where no numerical value is present
    if "includes taxes and charges" in price_string.lower() and not match:
        logger.debug(
            "extract_price_components: 'Includes taxes and charges' found, returning 0.0, ''."
        )
        return 0.0, ""  # Changed to empty string

    if not match:
        num_only_match = re.search(number_pattern, price_string)
        if not num_only_match:
            logger.debug(
                "extract_price_components: No number found, returning None, ''."
            )
            return None, ""  # Changed to empty string
        found_number_str = num_only_match.group(0)
        currency_symbol = ""  # Default currency_symbol to empty string
        logger.debug(
            f"extract_price_components: No currency match, found_number_str: {found_number_str}"
        )
    else:
        currency_symbol_found = match.group(1) or match.group(3)
        currency_symbol = (
            currency_symbol_found.upper()
            if currency_symbol_found
            else ""  # Default to empty string
        )
        # Normalize Rs to LKR
        if currency_symbol and currency_symbol.startswith("RS"):
            currency_symbol = "LKR"
        found_number_str = match.group(2)
        logger.debug(
            f"extract_price_components: Matched currency: {currency_symbol}, found_number_str: {found_number_str}"
        )

    if not found_number_str:
        logger.debug(
            f"extract_price_components: found_number_str is empty, returning 0.0, '{currency_symbol}'."
        )
        return 0.0, currency_symbol  # Changed to 0.0

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
    logger.debug(
        f"extract_price_components: processed_number before float conversion: {processed_number}"
    )

    try:
        result_value = float(processed_number)
        logger.debug(
            f"extract_price_components: Successfully parsed value: {result_value}, currency: {currency_symbol}"
        )
        return result_value, currency_symbol
    except ValueError:
        logger.debug(
            f"extract_price_components: ValueError for {processed_number}, returning 0.0, '{currency_symbol}'."
        )
        return 0.0, currency_symbol  # Changed to 0.0


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
        logger.debug(
            "extract_float_value: found_number_str is empty after match, returning None."
        )
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
    logger.debug(
        f"extract_float_value: processed_number before float conversion: {processed_number}"
    )

    try:
        result_value = float(processed_number)
        logger.debug(f"extract_float_value: Successfully parsed value: {result_value}")
        return result_value
    except ValueError:
        logger.debug(
            f"extract_float_value: ValueError for {processed_number}, returning None."
        )
        return None


def parse_distance_km(value_string: str | None) -> float | None:
    """
    Parses a distance string and returns distance in kilometers.
    Supports:
      - '2.8 km from downtown' → 2.8
      - '350 m from beach' → 0.35
      - 'Beachfront' → 0.0
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
    clicked_selectors = []  # Keep track of selectors that were clicked
    for selector in dismiss_selectors:
        logger.debug(f"Trying selector: {selector}")
        try:
            # Quickly check if the element is attached to the DOM first
            await page.wait_for_selector(selector, state='attached', timeout=500)
            dismiss = page.locator(selector).first
            if await dismiss.is_visible(
                timeout=3000
            ):  # Increased timeout for visibility check
                logger.info(f"Dismissing modal with selector: {selector}")
                await dismiss.scroll_into_view_if_needed()
                await dismiss.click(force=True)
                clicked_selectors.append(selector)  # Add to clicked list
                # Don't break here, some pages might have multiple modals to dismiss
        except Exception:
            logger.debug(
                f"Selector {selector} did not find a visible modal, attached element or failed to click."
            )
            continue

    # Wait for all clicked modals to disappear
    for selector in clicked_selectors:
        try:
            logger.debug(f"Waiting for modal with selector '{selector}' to disappear...")
            # Use wait_for on the specific locator that was clicked
            await page.locator(selector).wait_for(state="hidden", timeout=5000)
            logger.info(f"Modal with selector '{selector}' successfully disappeared.")
        except Exception:
            logger.debug(f"Modal with selector '{selector}' did not disappear within timeout.")


async def scroll_page_fully(page: Page, max_scroll_attempts: int = 10, scroll_timeout: int = 200) -> None:
    """
    Scroll the page multiple times until no new content loads.
    Args:
        page: Playwright page object.
        max_scroll_attempts: Maximum number of scroll attempts.
        scroll_timeout: Time in milliseconds to wait after each scroll for content to load.
    """
    try:
        logger.info("Starting full page scroll to load all content...")

        previous_height = 0
        scroll_count = 0
        no_change_count = 0

        while scroll_count < max_scroll_attempts:
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            # Wait for content to potentially load after scroll
            await page.wait_for_timeout(scroll_timeout) # Replaced asyncio.sleep

            current_height = await page.evaluate("document.body.scrollHeight")

            if current_height == previous_height:
                no_change_count += 1
                if no_change_count >= 3: # Increased tolerance for no change
                    logger.info(f"No new content loaded after {scroll_count} scrolls")
                    break
            else:
                no_change_count = 0

            previous_height = current_height
            scroll_count += 1
            logger.info(
                f"Scroll {scroll_count}/{max_scroll_attempts} - Height: {current_height}"
            )

        # Final scroll to top
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(scroll_timeout) # Replaced asyncio.sleep
        logger.info("Completed full page scroll")
        return
    except Exception as e:
        logger.error(f"Error during page scroll: {e}", exc_info=True)
        raise


async def extract_facility_group(page: Page, group_name: str) -> Optional[List[str]]:
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
            logger.info(
                f"Successfully extracted {len(facilities)} facilities for group: {group_name}"
            )
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

        rating_container = page.locator('[data-testid="rating-squares"]')

        squares = rating_container.locator(".e03979cfad")

        filled_squares = squares.locator(
            "span.fc70cba028.bdc459fcb4.f24706dc71:not(.e2cec97860)"
        )

        star_rating = await filled_squares.count()

        # Guest rating
        guest_rating = None

        rating_elem = page.locator("div.f63b14ab7a.dff2e52086")

        if await rating_elem.count() > 0:
            guest_rating = float((await rating_elem.first.inner_text()).strip())

        review_score_text = None

        score_text_elem = page.locator("div.f63b14ab7a.f546354b44")

        if await score_text_elem.count() > 0:
            review_score_text = (await score_text_elem.first.inner_text()).strip()

        # Review count
        review_count = None

        review_selectors = [
            'div.fff1944c52:has-text("reviews")',
            ".bui-review-score__review-count",
        ]

        for selector in review_selectors:
            try:
                review_elem = page.locator(selector).first
                if await review_elem.count() > 0:
                    text = (await review_elem.inner_text()).strip()
                    if text:
                        # "285 reviews" → 285
                        review_count = int(text.split()[0].replace(",", ""))
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

        # ===== PRICING =====
        logger.info("Extracting pricing...")

        # ===== PROPERTY HIGHLIGHTS =====
        logger.info("Extracting property highlights...")

        highlights = []

        # Locate all sections under property highlights
        sections = await page.locator("div.ph-sections div.ph-section").all()

        for section in sections[:15]:  # limit to first 15
            # First try <p> text - handle multiple matches if they occur
            p_elems = section.locator("p.ph-item span.ph-item-copy > span")
            if await p_elems.count() > 0:
                for p_elem_single in await p_elems.all(): # Iterate through all found elements
                    text = (await p_elem_single.inner_text()).strip()
                    if text:
                        highlights.append(text)

            # Then try <li> items inside the section (for lists like "Rooms with")
            li_elems = section.locator("ul li p.ph-item span.ph-item-copy > span") # Corrected to locator for consistency
            if await li_elems.count() > 0: # Check count before trying to get all
                for li_elem_single in await li_elems.all(): # Iterate through all found elements
                    li_text = (await li_elem_single.inner_text()).strip()
                    if li_text:
                        highlights.append(li_text)

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
            property_highlights=highlights if highlights else None,
        )

        logger.info(f"✓ Successfully scraped: {name}")
        return hotel_data

    except Exception as e:
        logger.error(f"✗ Error scraping {url}: {e}", exc_info=True)
        raise Exception(f"Error scraping {url}: {e}")


async def scrape_properties_data(page: Page, limit: int) -> List[PropertyListing]:
    hotels: List[PropertyListing] = []
    seen_links: set[str] = set()
    last_card_count = 0
    same_count = 0
    max_no_change_scrolls = 3 # How many times to scroll with no new cards before stopping

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
                # ---------- LINK ----------
                link = await card.locator('a[data-testid="title-link"]').get_attribute(
                    "href"
                )

                if not link or link in seen_links:
                    continue

                seen_links.add(link)

                if link.startswith("/"):
                    link = f"https://www.booking.com{link}"

                # ---------- NAME ----------
                name = await card.locator('[data-testid="title"]').inner_text()

                # ---------- ADDRESS ----------
                address = None
                address_el = card.locator('[data-testid="address"]')
                if await address_el.count():
                    address = (await address_el.inner_text()).strip()

                # ---------- STAR RATING ----------
                star_rating = 0.0  # Default value
                star_el = card.locator('[aria-label*="star"]')
                if await star_el.count():
                    extracted_star_rating_text = await star_el.get_attribute(
                        "aria-label"
                    )
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

                price_el_container = card.locator(
                    '[data-testid="price-and-discounted-price"]'
                )
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
                    if (
                        original_price_value is None
                        and discounted_price_value is not None
                    ):
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
                bed_details_el = card.locator(
                    "ul.d1e8dce286 li:first-child div.fff1944c52"
                )
                if await bed_details_el.count():
                    bed_details = (await bed_details_el.inner_text()).strip()

                # ---------- CANCELLATION POLICY ----------
                cancellation_policy = ""  # Default value
                cancellation_el = card.locator(
                    '[data-testid="cancellation-policy-icon"] + div div.fff1944c52'
                )
                if await cancellation_el.count():
                    cancellation_policy = (await cancellation_el.inner_text()).strip()

                # ---------- PREPAYMENT POLICY ----------
                prepayment_policy = ""  # Default value
                prepayment_el = card.locator(
                    '[data-testid="prepayment-policy-icon"] + div div.fff1944c52'
                )
                if await prepayment_el.count():
                    prepayment_policy = (await prepayment_el.inner_text()).strip()

                # ---------- AVAILABILITY MESSAGE ----------
                availability_message = ""  # Default value
                availability_el = card.locator(
                    "ul.d1e8dce286 li:last-child div.b7d3eb6716"
                )
                if await availability_el.count():
                    availability_message = (await availability_el.inner_text()).strip()

                # ---------- NIGHTS AND GUESTS ----------
                nights_and_guests = ""  # Default value
                nights_and_guests_el = card.locator(
                    '[data-testid="price-for-x-nights"]'
                )
                if await nights_and_guests_el.count():
                    nights_and_guests = (
                        await nights_and_guests_el.inner_text()
                    ).strip()

                hotels.append(
                    PropertyListing(
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
                        original_price_value=original_price_value,  # Now only value
                        original_price_currency=original_price_currency,
                        discounted_price_value=discounted_price_value,
                        discounted_price_currency=discounted_price_currency,
                        taxes_and_fees_value=taxes_value,
                        taxes_and_fees_currency=taxes_currency,
                    )
                )

                logger.info(f"✓ Listing scraped: {name}")

            except Exception as e:
                logger.warning(f"Failed to parse listing card: {e}")
                continue
        
        last_card_count = current_card_count

        # ---------- LOAD MORE ----------
        load_more = page.locator('button:has-text("Load more results")')
        if await load_more.count() and await load_more.is_visible():
            await load_more.click()
            await page.wait_for_load_state("networkidle")
            # After clicking load more, reset same_count as new content is expected
            same_count = 0
            continue

        # ---------- SCROLL AND WAIT FOR MORE CARDS ----------
        # Scroll to load more if no "Load more results" button was found or clicked
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # Instead of fixed sleep, wait for cards to increase
        await page.wait_for_timeout(200) # Give a small moment for scroll to take effect and new content to initiate loading

        new_card_count = await cards.count()

        if new_card_count == current_card_count:
            same_count += 1
            if same_count >= max_no_change_scrolls:
                logger.info(f"No new cards appeared after {max_no_change_scrolls} scrolls, stopping.")
                break
        else:
            same_count = 0 # Reset if new cards are found

    return hotels[:limit]
