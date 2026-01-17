from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


async def ensure_usd_and_english_uk(page: Page) -> None:
    """
    Ensures the Booking.com page is set to USD currency and English (UK) language.
    Also ensures all modals are properly closed before returning.
    
    Args:
        page: The Playwright page object
    """
    logger.info("Checking and setting currency to USD and language to English (UK)...")
    
    try:
        # First dismiss any existing modals
        await _force_close_all_modals(page)
        
        # Check and set currency to USD
        await _set_currency_to_usd(page)
        
        # Check and set language to English (UK)
        await _set_language_to_english_uk(page)
        
        # Final check - ensure all modals are closed
        await _force_close_all_modals(page)
        
        logger.info("Successfully ensured USD currency and English (UK) language")
        
    except Exception as e:
        logger.error(f"Error setting locale preferences: {e}")
        # Try to close any open modals even if there was an error
        await _force_close_all_modals(page)
        raise


async def _force_close_all_modals(page: Page) -> None:
    """Force close any open currency or language selector modals."""
    close_selectors = [
        'button[aria-label*="Close currency selector"]',
        'button[aria-label*="Close language selector"]',
        'button[data-testid="selection-modal-close"]',
    ]
    
    for selector in close_selectors:
        try:
            close_button = page.locator(selector).first
            if await close_button.is_visible(timeout=1000):
                logger.debug(f"Closing modal with selector: {selector}")
                await close_button.click(force=True, timeout=2000)
                await page.wait_for_timeout(500)  # Brief wait for modal to close
        except Exception:
            pass  # Modal not found or already closed


async def _set_currency_to_usd(page: Page) -> None:
    """Sets the currency to USD if not already set."""
    try:
        # Click the currency picker trigger button
        currency_button = page.locator('button[data-testid="header-currency-picker-trigger"]')
        await currency_button.wait_for(state="visible", timeout=5000)
        
        # Check current currency text
        current_currency = await currency_button.inner_text()
        logger.debug(f"Current currency: {current_currency}")
        
        if "USD" in current_currency:
            logger.info("Currency is already set to USD")
            return
        
        # Open currency selector modal
        logger.info("Opening currency selector...")
        await currency_button.click(timeout=5000)
        
        # Wait for modal to appear - use a more flexible selector
        try:
            await page.wait_for_selector('.Picker_selection-list', state="visible", timeout=5000)
        except Exception:
            logger.debug("Modal might already be open or different structure")
        
        # Find USD option using the currency code div
        # This works regardless of the language because USD is always "USD"
        usd_button = page.locator(
            'button[data-testid="selection-item"]',
            has=page.locator('.CurrencyPicker_currency:text("USD")')
        ).first
        
        await usd_button.wait_for(state="visible", timeout=5000)
        
        # Check if USD is already selected
        is_selected = await usd_button.get_attribute("aria-current")
        if is_selected == "true":
            logger.info("USD is already selected in the modal")
            # Close modal
            await _force_close_all_modals(page)
            return
        
        logger.info("Selecting USD currency...")
        await usd_button.click(timeout=5000)
        
        # Wait for the selection to take effect
        await page.wait_for_timeout(1000)
        
        # Ensure modal is closed
        await _force_close_all_modals(page)
        
        logger.info("Currency set to USD successfully")
        
    except Exception as e:
        logger.warning(f"Could not set currency to USD: {e}")
        # Ensure modal is closed even on error
        await _force_close_all_modals(page)


async def _set_language_to_english_uk(page: Page) -> None:
    """Sets the language to English (UK) if not already set."""
    try:
        # Wait a moment to ensure previous operations completed
        await page.wait_for_timeout(500)
        
        # Click the language picker trigger button
        language_button = page.locator('button[data-testid="header-language-picker-trigger"]')
        await language_button.wait_for(state="visible", timeout=5000)
        
        # Check current language by looking for the UK flag image
        uk_flag = language_button.locator('img[src*="Gb@3x.png"]')
        is_uk_flag_visible = await uk_flag.count() > 0
        
        if is_uk_flag_visible:
            logger.info("Language is already set to English (UK)")
            return
        
        # Open language selector modal
        logger.info("Opening language selector...")
        await language_button.click(force=True, timeout=5000)
        
        # Wait for modal to appear
        try:
            await page.wait_for_selector('.Picker_selection-list', state="visible", timeout=5000)
        except Exception:
            logger.debug("Modal might already be open or different structure")
        
        # Find and click English (UK) option
        # We look for the button with lang="en-gb"
        en_uk_button = page.locator('button[data-testid="selection-item"][lang="en-gb"]').first
        
        await en_uk_button.wait_for(state="visible", timeout=5000)
        
        # Check if English (UK) is already selected
        is_selected = await en_uk_button.get_attribute("aria-current")
        if is_selected == "true":
            logger.info("English (UK) is already selected in the modal")
            # Close modal
            await _force_close_all_modals(page)
            return
        
        logger.info("Selecting English (UK) language...")
        await en_uk_button.click(timeout=5000)
        
        # Wait for page to reload/update with new language
        # Language change often triggers a reload
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            logger.debug("Page did not reload after language change")
        
        # Wait for any transitions
        await page.wait_for_timeout(1500)
        
        # Ensure modal is closed (might not exist after reload)
        await _force_close_all_modals(page)
        
        logger.info("Language set to English (UK) successfully")
        
    except Exception as e:
        logger.warning(f"Could not set language to English (UK): {e}")
        # Ensure modal is closed even on error
        await _force_close_all_modals(page)


async def modal_dismisser(page: Page) -> None:
    """Dismisses sign-in popups and waits for any modal to disappear."""
    logger.info("Attempting to dismiss any visible modals...")
    
    # First close any currency/language modals that might be open
    await _force_close_all_modals(page)
    
    dismiss_selectors = [
        'button[aria-label="Dismiss sign-in info."]',
        "button.de576f5064.b46cd7aad7.e26a59bb37",
        'div.a5c71b0007 button[type="button"]',
        'button[aria-label="Close"]',
        'button:has-text("Close")',
    ]
    clicked_selectors = []
    
    for selector in dismiss_selectors:
        logger.debug(f"Trying selector: {selector}")
        try:
            await page.wait_for_selector(selector, state='attached', timeout=500)
            dismiss = page.locator(selector).first
            if await dismiss.is_visible(timeout=3000):
                logger.info(f"Dismissing modal with selector: {selector}")
                await dismiss.scroll_into_view_if_needed()
                await dismiss.click(force=True)
                clicked_selectors.append(selector)
        except Exception:
            logger.debug(
                f"Selector {selector} did not find a visible modal, attached element or failed to click."
            )
            continue

    # Wait for all clicked modals to disappear
    for selector in clicked_selectors:
        try:
            logger.debug(f"Waiting for modal with selector '{selector}' to disappear...")
            await page.locator(selector).wait_for(state="hidden", timeout=5000)
            logger.info(f"Modal with selector '{selector}' successfully disappeared.")
        except Exception:
            logger.debug(f"Modal with selector '{selector}' did not disappear within timeout.")