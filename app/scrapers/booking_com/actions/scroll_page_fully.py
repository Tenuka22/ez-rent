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
            await page.wait_for_timeout(scroll_timeout)

            current_height = await page.evaluate("document.body.scrollHeight")

            if current_height == previous_height:
                no_change_count += 1
                if no_change_count >= 3:
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
        await page.wait_for_timeout(scroll_timeout)
        logger.info("Completed full page scroll")
        return
    except Exception as e:
        logger.error(f"Error during page scroll: {e}", exc_info=True)
        raise
