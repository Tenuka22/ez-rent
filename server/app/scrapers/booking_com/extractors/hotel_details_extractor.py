from typing import List, Optional

from playwright.async_api import Page

from app.data_models import HotelDetails
from app.utils.logger import logger
from app.scrapers.booking_com.actions.scroll_page_fully import scroll_page_fully
from app.scrapers.booking_com.actions.extract_facility_group import (
    extract_facility_group,
)
from app.scrapers.booking_com.utils import modal_dismisser,ensure_usd_and_english_uk


async def scrape_hotel_data(page: Page, url: str) -> HotelDetails:
    """Scrape detailed information from a single hotel page."""
    try:
        logger.info(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=60000)

        # Dismiss modal first
        await modal_dismisser(page)
        await ensure_usd_and_english_uk(page)

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