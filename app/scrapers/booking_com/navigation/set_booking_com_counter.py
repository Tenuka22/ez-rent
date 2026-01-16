from playwright.async_api import Page

from app.utils.logger import logger


async def set_booking_com_counter(page: Page, input_id: str, target: int) -> None:
    """
    Sets the value of a counter on booking.com (e.g., number of adults, rooms).

    Args:
        page: Playwright page object.
        input_id: The ID of the input element associated with the counter.
        target: The target value to set the counter to.
    """
    logger.info(f"Setting counter for {input_id} to target: {target}")
    try:
        container = page.locator(f"input#{input_id}").locator("..").locator("..")
        value_span = container.locator('span.e32aa465fd[aria-hidden="true"]').first
        buttons = container.locator("button")
        minus_btn = buttons.nth(0)
        plus_btn = buttons.nth(1)

        current = int(await value_span.inner_text())
        logger.debug(f"Initial value for {input_id}: {current}")

        # Increase
        while current < target:
            if not await plus_btn.is_enabled():
                logger.warning(
                    f"Cannot increase {input_id} further, plus button disabled."
                )
                break
            await plus_btn.click()
            current += 1
            logger.debug(f"Increased {input_id} to {current}")

        # Decrease
        while current > target:
            if not await minus_btn.is_enabled():
                logger.warning(
                    f"Cannot decrease {input_id} further, minus button disabled."
                )
                break
            await minus_btn.click()
            current -= 1
            logger.debug(f"Decreased {input_id} to {current}")
        logger.info(f"Counter for {input_id} successfully set to {target}.")
        return
    except Exception as e:
        logger.error(
            f"Error setting booking.com counter for {input_id}: {e}", exc_info=True
        )
        raise Exception(str(e))
