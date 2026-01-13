import asyncio

from returns.result import Failure

from src.scrapers.booking_com import scrape_booking_com_data


async def main():
    data_result = await scrape_booking_com_data("Unawatuna")
    if isinstance(data_result, Failure):
        print(f"Scraping failed: {data_result.failure()}")
        return

    data = data_result.unwrap()
    print("Hello from ez-rent!")


if __name__ == "__main__":
    asyncio.run(main())
