from typing import List, Optional

from playwright.async_api import Page

from app.utils.logger import logger


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
