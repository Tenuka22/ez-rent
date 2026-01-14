from playwright.async_api import Page
from app.utils.logger import logger

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
