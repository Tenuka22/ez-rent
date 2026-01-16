import re
from typing import Optional

from app.utils.logger import logger


def extract_price_components(
    price_string: str | None,
) -> tuple[float | None, str]:
    """
    Extracts numerical price value and currency from a price string.
    Handles various formats, currency symbols, and decimal/thousands separators.

    Args:
        price_string (str | None): The input string containing price information.

    Returns:
        tuple[float | None, str]: A tuple containing the extracted price (float)
        and currency (str). Returns (None, "") if no valid number is found,
        or (0.0, currency) if "includes taxes and charges" is present without a number.
    """
    logger.debug(f"extract_price_components: Input price_string: {price_string}")
    if not isinstance(price_string, str):
        logger.debug(
            "extract_price_components: Input is not a string, returning None, ''."
        )
        return None, ""

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
        return 0.0, ""

    if not match:
        num_only_match = re.search(number_pattern, price_string)
        if not num_only_match:
            logger.debug(
                "extract_price_components: No number found, returning None, ''."
            )
            return None, ""
        found_number_str = num_only_match.group(0)
        currency_symbol = ""
        logger.debug(
            f"extract_price_components: No currency match, found_number_str: {found_number_str}"
        )
    else:
        currency_symbol_found = match.group(1) or match.group(3)
        currency_symbol = (
            currency_symbol_found.upper() if currency_symbol_found else ""
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
        return 0.0, currency_symbol

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
        return 0.0, currency_symbol
