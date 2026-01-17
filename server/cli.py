import asyncio
from typing import Literal, Optional

import typer

from app.core_logic import run_prediction_flow
from app.utils.logger import logger

cli_app = typer.Typer()


# --- CLI Commands ---


@cli_app.command(help="Run the scraping and prediction process via the command line.")
def run(
    predictor_house_data_source: Literal["scrape", "manual"] = typer.Option(
        "scrape",
        help="Source of data: 'scrape' from Booking.com or 'manual' entry.",
        case_sensitive=False,
    ),
    destination: str = typer.Option(
        "Unawatuna", help="Destination for scraping (e.g., city, region)."
    ),
    adults: int = typer.Option(2, help="Number of adults for the booking."),
    rooms: int = typer.Option(1, help="Number of rooms for the booking."),
    properties_limit: int = typer.Option(
        300, help="Maximum number of properties to scrape."
    ),
    hotel_details_limit: int = typer.Option(
        100, help="Maximum number of hotel details to scrape."
    ),
    force_refetch: bool = typer.Option(
        False,
        "--force-refetch",
        help="If set, forces refetching of data even if cached.",
    ),
    prediction_model_type: Literal["basic", "advanced"] = typer.Option(
        "basic",
        help="Type of prediction model to use: 'basic' or 'advanced'.",
        case_sensitive=False,
    ),
    target_hotel_name: Optional[str] = typer.Option(
        "Sunset Mirage Villa",
        help="Specific hotel name to target during scraping. Only used when data_source is 'scrape'.",
    ),
):
    """
    Command-line interface to run the Ez-Rent scraper and prediction.
    """
    try:
        asyncio.run(
            run_prediction_flow(
                data_source=predictor_house_data_source,
                destination=destination,
                adults=adults,
                rooms=rooms,
                properties_limit=properties_limit,
                hotel_details_limit=hotel_details_limit,
                force_refetch=force_refetch,
                prediction_model_type=prediction_model_type,
                target_hotel_name=target_hotel_name,
            )
        )
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"CLI Error: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    cli_app()
