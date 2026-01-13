import os
import time

from playwright.async_api import Page
from returns.result import Failure, Result, Success

from src.scrapers.booking_com.browser import modal_dismisser
from src.scrapers.booking_com.playwright_urls import BookingComUrls
from src.utils.logger import logger


async def set_booking_com_counter(
    page: Page, input_id: str, target: int
) -> Result[None, str]:
    """
    Sets the value of a counter on booking.com (e.g., number of adults, rooms).

    Args:
        page: Playwright page object.
        input_id: The ID of the input element associated with the counter.
        target: The target value to set the counter to.

    Returns:
        Result[None, str]: Success(None) if the counter is set, Failure with an error message otherwise.
    """
    try:
        container = page.locator(f"input#{input_id}").locator("..").locator("..")
        value_span = container.locator('span.e32aa465fd[aria-hidden="true"]').first
        buttons = container.locator("button")
        minus_btn = buttons.nth(0)
        plus_btn = buttons.nth(1)

        current = int(await value_span.inner_text())

        # Increase
        while current < target:
            if not await plus_btn.is_enabled():
                break  # can't increase, exit loop
            await plus_btn.click()
            current += 1

        # Decrease
        while current > target:
            if not await minus_btn.is_enabled():
                break  # can't decrease, exit loop
            await minus_btn.click()
            current -= 1
        return Success(None)
    except Exception as e:
        logger.error(f"Error setting booking.com counter for {input_id}: {e}")
        return Failure(str(e))

async def goto_properties_page(
    page: Page,
    destination: str,
    urls: BookingComUrls,
    adults: int = 2,
    rooms: int = 1,
) -> Result[None, str]:
    try:
        # Go to home page
        await page.goto(urls.home, wait_until="networkidle", timeout=60_000)
        dismiss_result = await modal_dismisser(page)
        if isinstance(dismiss_result, Failure):
            return Failure(f"Failed to dismiss modal: {dismiss_result.failure()}")
        # 1️⃣ Date picker
        date_button = page.locator('[data-testid="searchbox-dates-container"]')
        await date_button.wait_for(state="visible", timeout=5000)
        await date_button.click()

        # Flexible dates logic (weekend + months)
        flexible_btn = page.locator("button#flexible-searchboxdatepicker-tab-trigger")
        await flexible_btn.wait_for(state="visible", timeout=5000)
        await flexible_btn.click()

        flexible_modal = page.locator(
            'div[data-testid="flexible-searchboxdatepicker-tab"]'
        )
        try:
            await flexible_modal.wait_for(state="visible", timeout=5000)
        except Exception:
            logger.debug("Flexible modal did not appear, continuing...")

        # Select weekend option
        weekend_btn = page.locator(
            'input[value="weekend"], button:has-text("A weekend")'
        ).first
        if await weekend_btn.count() > 0 and await weekend_btn.is_visible(timeout=3000):
            await weekend_btn.click()

        # Select months
        month_buttons = page.locator('label[data-testid="flexible-dates-month"]')
        for i in range(min(3, await month_buttons.count())):
            await month_buttons.nth(i).click()

        # ✅ Select length of stay (required for "Select dates" to be clickable)
        los_radio = page.locator('input[name="flexible_los"][value="5_1"]')  # A weekend
        await los_radio.wait_for(state="visible", timeout=3000)
        await los_radio.click()

        # Confirm dates
        select_dates_btn = page.locator('button:has-text("Select dates")')
        await select_dates_btn.wait_for(state="visible", timeout=5000)
        await select_dates_btn.click()

        # 2️⃣ Occupancy
        occupancy_btn = page.locator('[data-testid="occupancy-config"]')
        await occupancy_btn.wait_for(state="visible", timeout=5000)
        await occupancy_btn.click()

        adults_counter_result = await set_booking_com_counter(page, "group_adults", adults)
        if isinstance(adults_counter_result, Failure):
            return Failure(
                f"Failed to set adults counter: {adults_counter_result.failure()}"
            )

        children_counter_result = await set_booking_com_counter(page, "group_children", 0)
        if isinstance(children_counter_result, Failure):
            return Failure(
                f"Failed to set children counter: {children_counter_result.failure()}"
            )

        rooms_counter_result = await set_booking_com_counter(page, "no_rooms", rooms)
        if isinstance(rooms_counter_result, Failure):
            return Failure(
                f"Failed to set rooms counter: {rooms_counter_result.failure()}"
            )

        done_btn = page.locator('button:has-text("Done")')
        await done_btn.wait_for(state="visible", timeout=5000)
        await done_btn.click()

        # 3️⃣ Destination input (type last, then select from dropdown)
        dest_input = page.locator('input[name="ss"]').first
        await dest_input.wait_for(state="visible", timeout=10000)
        await dest_input.click(force=True)
        await dest_input.fill("")  # Clear input
        await dest_input.type(destination, delay=50)

        # Try selecting autocomplete options up to 3 times
        autocomplete_list = page.locator(
            'div[data-testid="autocomplete-results-options"] > ul > li'
        )
        selected = False
        for attempt in range(3):
            count = await autocomplete_list.count()
            if count > 0:
                # Click the first option
                await autocomplete_list.nth(0).click()
                selected = True
                break
            await page.wait_for_timeout(500)  # wait before retrying

        if not selected:
            logger.info("No autocomplete option found, using typed destination as fallback.")

        # Click the Search button
        search_btn = page.locator('span:has-text("Search")').first
        await search_btn.wait_for(state="visible", timeout=5000)
        await search_btn.click()

        # Wait for search results
        await page.wait_for_load_state("networkidle", timeout=30_000)
        return Success(None)

    except Exception as e:
        os.makedirs("./errors", exist_ok=True)
        await page.screenshot(
            path=f"./errors/{destination}_a{adults}_r{rooms}_{int(time.time())}.png"
        )
        logger.exception(e)
        return Failure(str(e))
