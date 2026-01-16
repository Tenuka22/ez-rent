import os
import time

from playwright.async_api import Page

from app.scrapers.booking_com.navigation.set_booking_com_counter import (
    set_booking_com_counter,
)
from app.scrapers.booking_com.playwright_urls import BookingComUrls
from app.scrapers.booking_com.utils import modal_dismisser
from app.utils.logger import logger


async def goto_properties_page(
    page: Page,
    destination: str,
    urls: BookingComUrls,
    adults: int = 2,
    rooms: int = 1,
) -> None:
    """
    Navigates to the Booking.com properties search results page for the specified criteria.

    Args:
        page (Page): Playwright Page object.
        destination (str): The destination (city, region) to search for.
        urls (BookingComUrls): An instance of BookingComUrls to get base URLs.
        adults (int): The number of adults for the booking. Defaults to 2.
        rooms (int): The number of rooms for the booking. Defaults to 1.

    Raises:
        Exception: If an error occurs during navigation or interaction.
    """
    logger.info(
        f"Navigating to properties page for destination: '{destination}', adults: {adults}, rooms: {rooms}"
    )
    try:
        # Go to home page
        logger.info(f"Going to Booking.com home page: {urls.home}")
        await page.goto(urls.home, wait_until="networkidle", timeout=60_000)
        await modal_dismisser(page)

        # 1️⃣ Date picker
        logger.info("Opening date picker.")
        date_button = page.locator('[data-testid="searchbox-dates-container"]')
        await date_button.wait_for(state="visible", timeout=5000)
        await date_button.click()

        # Flexible dates logic (weekend + months)
        logger.info("Selecting flexible dates option.")
        flexible_btn = page.locator("button#flexible-searchboxdatepicker-tab-trigger")
        await flexible_btn.wait_for(state="visible", timeout=5000)
        await flexible_btn.click()

        flexible_modal = page.locator(
            'div[data-testid="flexible-searchboxdatepicker-tab"]'
        )
        try:
            await flexible_modal.wait_for(state="visible", timeout=5000)
            logger.debug("Flexible modal appeared.")
        except Exception:
            logger.debug("Flexible modal did not appear, continuing...")

        # Select weekend option
        logger.info("Selecting weekend option for flexible dates.")
        weekend_btn = page.locator(
            'input[value="weekend"], button:has-text("A weekend")'
        ).first
        if await weekend_btn.count() > 0 and await weekend_btn.is_visible(timeout=3000):
            await weekend_btn.click()
            logger.debug("Weekend option clicked.")
        else:
            logger.debug("Weekend option not found or not visible.")

        # Select months
        logger.info("Selecting months for flexible dates.")
        month_buttons = page.locator('label[data-testid="flexible-dates-month"]')
        num_months_to_select = min(3, await month_buttons.count())
        for i in range(num_months_to_select):
            await month_buttons.nth(i).click()
            logger.debug(f"Selected month {i + 1}.")

        # ✅ Select length of stay (required for "Select dates" to be clickable)
        logger.info("Selecting length of stay.")
        los_radio = page.locator('input[name="flexible_los"][value="5_1"]')  # A weekend
        await los_radio.wait_for(state="visible", timeout=3000)
        await los_radio.click()
        logger.debug("Length of stay 'A weekend' selected.")

        # Confirm dates
        logger.info("Confirming dates.")
        select_dates_btn = page.locator('button:has-text("Select dates")')
        await select_dates_btn.wait_for(state="visible", timeout=5000)
        await select_dates_btn.click()
        logger.debug("Select dates button clicked.")

        # 2️⃣ Occupancy
        logger.info("Opening occupancy configuration.")
        occupancy_btn = page.locator('[data-testid="occupancy-config"]')
        await occupancy_btn.wait_for(state="visible", timeout=5000)
        await occupancy_btn.click()
        logger.debug("Occupancy button clicked.")

        await set_booking_com_counter(page, "group_adults", adults)
        await set_booking_com_counter(
            page, "group_children", 0
        )  # Assuming 0 children for now
        await set_booking_com_counter(page, "no_rooms", rooms)

        logger.info("Clicking Done on occupancy configuration.")
        done_btn = page.locator('button:has-text("Done")')
        await done_btn.wait_for(state="visible", timeout=5000)
        await done_btn.click()
        logger.debug("Done button clicked on occupancy configuration.")

        # 3️⃣ Destination input (type last, then select from dropdown)
        logger.info(f"Entering destination: '{destination}'")
        dest_input = page.locator('input[name="ss"]').first
        await dest_input.wait_for(state="visible", timeout=10000)
        await dest_input.click(force=True)
        await dest_input.fill("")  # Clear input
        await dest_input.type(destination, delay=50)
        logger.debug("Destination typed into input field.")
        await page.wait_for_timeout(2000)

        # Try selecting autocomplete options up to 3 times
        autocomplete_list = page.locator(
            'div[data-testid="autocomplete-results-options"] > ul > li'
        )
        selected = False
        num_options = await autocomplete_list.count()
        logger.debug(f"Found {num_options} autocomplete options.")

        for i in range(min(num_options, 5)):  # Check up to 5 options for a match
            option = autocomplete_list.nth(i)
            option_text = await option.inner_text()
            logger.debug(f"Autocomplete option {i}: {option_text}")
            if option_text and option_text.lower().startswith(destination.lower()):
                await option.click()
                selected = True
                logger.info(
                    f"Autocomplete option '{option_text}' selected for '{destination}'."
                )
                break

        if not selected:
            logger.info(
                "No matching autocomplete option found, proceeding with typed destination."
            )

        # Click the Search button
        logger.info("Clicking search button.")
        search_btn = page.locator('span:has-text("Search")').first
        await search_btn.wait_for(state="visible", timeout=5000)
        await search_btn.click()
        logger.debug("Search button clicked.")

        # Wait for search results
        logger.info("Waiting for search results to load.")
        await page.wait_for_load_state("networkidle", timeout=30_000)
        logger.info("Search results page loaded.")
        return

    except Exception as e:
        logger.error(
            f"Error navigating to properties page for {destination}: {e}", exc_info=True
        )
        os.makedirs("./errors", exist_ok=True)
        screenshot_path = (
            f"./errors/{destination}_a{adults}_r{rooms}_{int(time.time())}.png"
        )
        await page.screenshot(path=screenshot_path)
        logger.error(f"Screenshot saved to {screenshot_path}")
        raise Exception(str(e))
