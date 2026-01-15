from typing import List, Optional

from playwright.async_api import Page

from app.utils.logger import logger


async def scroll_page_fully(
    page: Page, max_scroll_attempts: int = 10, scroll_timeout: int = 200
) -> None:
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
            await page.wait_for_timeout(scroll_timeout)  # Replaced asyncio.sleep

            current_height = await page.evaluate("document.body.scrollHeight")

            if current_height == previous_height:
                no_change_count += 1
                if no_change_count >= 3:  # Increased tolerance for no change
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
        await page.wait_for_timeout(scroll_timeout)  # Replaced asyncio.sleep
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
