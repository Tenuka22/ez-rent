from typing import Any


def get_manual_input(prompt: str, type_func: type, default: Any = None) -> Any:
    """Helper function to get validated manual input."""
    while True:
        user_input = input(f"{prompt} (default: {default}): ")
        if not user_input and default is not None:
            return default
        try:
            return type_func(user_input)
        except ValueError:
            print(f"Invalid input. Please enter a {type_func.__name__}.")