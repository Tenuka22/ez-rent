import re
from typing import Optional

from app.utils.logger import logger


def extract_float_value(value_string: str | None) -> float | None:
    """
    Extracts a float numerical value from a given string.
    Handles various formats, decimal/thousands separators, and removes non-numeric characters.

    Args:
        value_string (str | None): The input string from which to extract the float.

    Returns:
        float | None: The extracted float value, or None if no valid number is found.
    """
    logger.debug(f"extract_float_value: Input value_string: {value_string}")
    if not isinstance(value_string, str):
        logger.debug("extract_float_value: Input is not a string, returning None.")
        return None

    value_string = value_string.replace("\u202f", " ").strip()
    match = re.search(r"(\d{1,3}(?:[.,\s]?\d{3})*(?:[.,]\d{1,2})?)", value_string)
    if not match:
        logger.debug("extract_float_value: No number found in string, returning None.")
        return None

    found_number_str = match.group(1)
    if not found_number_str:
        logger.debug(
            "extract_float_value: found_number_str is empty after match, returning None."
        )
        return None
    logger.debug(f"extract_float_value: found_number_str: {found_number_str}")

    cleaned_number_str = found_number_str.replace(" ", "")
    logger.debug(f"extract_float_value: cleaned_number_str: {cleaned_number_str}")
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
        f"extract_float_value: processed_number before float conversion: {processed_number}"
    )

    try:
        result_value = float(processed_number)
        logger.debug(f"extract_float_value: Successfully parsed value: {result_value}")
        return result_value
    except ValueError:
        logger.debug(
            f"extract_float_value: ValueError for {processed_number}, returning None."
        )
        return None
