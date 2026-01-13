# 🚀 ez-rent

> Automated web scraping of Booking.com for academic research and market trend analysis.

![Build](https://img.shields.io/github/actions/workflow/status/Tenuka22/ez-rent/ci.yml?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Language](https://img.shields.io/badge/python-3.9+-blue?style=flat-square)

---

## 🎯 Table of Contents

-   [✨ Features](#-features)
-   [🚀 Quick Start](#-quick-start)
-   [📦 Installation](#-installation)
-   [💻 Usage](#-usage)
-   [⚙️ Configuration](#️-configuration)
-   [📖 Examples](#-examples)
-   [📚 API Reference](#-api-reference)
-   [🤝 Contributing](#-contributing)
-   [📝 License](#-license)

---

## ✨ Features

`ez-rent` is a robust and efficient web scraper designed to extract detailed hotel and property data from Booking.com. It's built for researchers and analysts looking to gather comprehensive datasets for academic studies, price prediction, or market trend analysis.

*   🎯 **Asynchronous Web Scraping**: Leverages `asyncio` and `Playwright` for high-performance, concurrent scraping of multiple pages.
*   ⚡ **Dynamic Content Handling**: Navigates Booking.com pages, sets search parameters, handles modal popups (like sign-in prompts), and performs full page scrolling to load all dynamic content.
*   📦 **Detailed Data Extraction**: Scrapes extensive information for properties and individual hotels, including amenities, ratings, pricing, and availability trends.
*   🔧 **Robust Error Handling**: Incorporates `returns` (a Result type implementation) for predictable and functional error management, ensuring stable operation.
*   📚 **Data Persistence & Caching**: Saves scraped data into CSV files and implements a URL caching mechanism to prevent redundant requests and optimize scraping efficiency.

---

## 🚀 Quick Start

Get `ez-rent` up and running to start scraping Booking.com data. Since `ez-rent` is designed as a library of functions, you'll need to construct your own entry point script.

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/Tenuka22/ez-rent.git
    cd ez-rent
    ```

2.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Playwright browsers**:

    ```bash
    playwright install
    ```

4.  **Create your scraping script**:
    Start by importing and calling the core functions. See the [Usage](#-usage) and [Examples](#-examples) sections for detailed guidance on how to orchestrate a scraping run.

---

## 📦 Installation

This project requires Python 3.9+ and uses `pip` for dependency management.

### Prerequisites

*   **Python**: Ensure you have Python 3.9 or newer installed.
    ```bash
    python --version
    ```
*   **Playwright Browsers**: Playwright needs browser binaries. Install them after installing `playwright` itself.

### Installation Steps

1.  **Clone the Repository**:
    Obtain the source code by cloning the `ez-rent` GitHub repository.
    ```bash
    git clone https://github.com/Tenuka22/ez-rent.git
    cd ez-rent
    ```

2.  **Install Python Dependencies**:
    Install all required Python packages using `pip`.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Playwright Browser Binaries**:
    Install the necessary browser binaries (Chromium, Firefox, WebKit) for Playwright.
    ```bash
    playwright install
    ```
    > 💡 **Tip**: For a headless environment, you might only need specific browsers or can configure Playwright to run in headless mode.

---

## 💻 Usage

`ez-rent` provides a set of modular functions for web scraping. As noted by Tenuka22 in a recent commit (`a7a5317`), the project is structured for programmatic use, requiring you to call the exposed functions as needed from your own Python script.

### Intended Use Case

The primary intended use case for `ez-rent` is academic research on hotel pricing, availability trends, or geographical data analysis. The future integration of machine learning libraries like `scikit-learn`, `seaborn`, and `tensorflow` aims to support advanced features such as price prediction and market trend analysis.

### Basic Scrape (Programmatic Example)

Here's a conceptual example of how you might initiate a scrape for a specific destination. You would typically create a `main.py` or similar script within the project folder or an external project.

```python
import asyncio
from typing import List, Dict, Any
from pathlib import Path

# Assume these are your scraper's core functions/classes
from ez_rent.booking_scraper import BookingComScraper # Hypothetical path
from ez_rent.data_writer import save_data_to_csv # Hypothetical path

async def main():
    destination = "New York"
    adults = 2
    rooms = 1
    output_dir = Path("scraped_data")
    output_dir.mkdir(exist_ok=True)

    scraper = BookingComScraper(
        headless=True,  # Set to False to see the browser UI
        cache_enabled=True
    )

    try:
        print(f"🚀 Starting scrape for {destination} with {adults} adults and {rooms} room(s)...")
        # Navigate to search results and collect property URLs
        search_results: List[Dict[str, Any]] = await scraper.search_and_collect_urls(
            destination=destination,
            adults=adults,
            rooms=rooms
        )

        if search_results:
            print(f"🔍 Found {len(search_results)} properties. Scraping details...")
            # Concurrently scrape details for all found properties
            all_property_details = await scraper.scrape_multiple_property_details(
                search_results # This list likely contains URLs and basic info
            )

            # Process and save the collected data
            if all_property_details:
                print(f"✅ Successfully scraped details for {len(all_property_details)} properties.")
                output_path = output_dir / f"{destination.replace(' ', '_').lower()}_hotels.csv"
                save_data_to_csv(all_property_details, output_path)
                print(f"💾 Data saved to {output_path}")
            else:
                print("❌ No detailed property data collected.")
        else:
            print(f"❌ No properties found for {destination}.")

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
    finally:
        await scraper.close()
        print("Scraper closed.")

if __name__ == "__main__":
    asyncio.run(main())
```

To run this script:
```bash
python your_main_script.py
```

### Expected Output

The script above would produce a CSV file (e.g., `scraped_data/new_york_hotels.csv`) containing detailed information for each property found, similar to this structure:

```csv
name,address,rating,review_score,price,amenities,description,url
The Plaza Hotel,"Fifth Avenue at Central Park South, New York",4.5,9.2,"$750.00","WiFi,Spa,Restaurant",A historic luxury hotel...,https://www.booking.com/hotel/us/the-plaza-hotel.html
...
```

---

## ⚙️ Configuration

`ez-rent` is primarily configured through parameters passed to its functions and class constructors. There are no external configuration files (e.g., `.ini`, `.json`) currently.

### `BookingComScraper` Initialization Options

When instantiating the main scraper class, you can control its behavior:

| Parameter     | Type      | Default | Description                                                              |
| :------------ | :-------- | :------ | :----------------------------------------------------------------------- |
| `headless`    | `bool`    | `True`  | If `True`, the browser runs in the background. Set to `False` to see the browser UI. |
| `cache_enabled` | `bool`    | `False` | If `True`, previously visited URLs are cached to prevent redundant requests. |
| `timeout`     | `int`     | `30000` | Default timeout (in milliseconds) for Playwright actions.                |
| `proxy`       | `Optional[str]` | `None`  | Proxy server URL (e.g., `http://user:pass@host:port`) to use for requests. |
| `user_agent`  | `Optional[str]` | `None`  | Custom User-Agent string for the browser.                              |

**Example:**

```python
from ez_rent.booking_scraper import BookingComScraper # Hypothetical path

# Run in headful mode with caching
scraper_verbose = BookingComScraper(
    headless=False,
    cache_enabled=True,
    timeout=60000 # 60 seconds
)

# Run headless with a proxy
scraper_proxied = BookingComScraper(
    headless=True,
    proxy="http://myproxy.com:8080",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"
)
```

---

## 📖 Examples

Here are more comprehensive examples demonstrating how to use `ez-rent` for different scraping scenarios.

### Example 1: Scrape Multiple Destinations Concurrently

This example shows how to scrape data for several destinations simultaneously, saving each to its own CSV file.

```python
import asyncio
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd

from ez_rent.booking_scraper import BookingComScraper
from ez_rent.data_writer import save_data_to_csv # Assuming a utility to save data

async def scrape_destination(scraper: BookingComScraper, destination: str, adults: int, rooms: int, output_dir: Path):
    """Orchestrates scraping for a single destination and saves data."""
    print(f"--- Starting scrape for {destination} ---")
    try:
        search_results = await scraper.search_and_collect_urls(
            destination=destination,
            adults=adults,
            rooms=rooms
        )

        if search_results:
            print(f"  Found {len(search_results)} properties in {destination}. Scraping details...")
            property_details = await scraper.scrape_multiple_property_details(search_results)

            if property_details:
                output_path = output_dir / f"{destination.replace(' ', '_').lower()}_hotels.csv"
                save_data_to_csv(property_details, output_path)
                print(f"  ✅ Data for {destination} saved to {output_path}")
            else:
                print(f"  ❌ No detailed property data collected for {destination}.")
        else:
            print(f"  ❌ No properties found for {destination}.")

    except Exception as e:
        print(f"  ⚠️ Error scraping {destination}: {e}")
    print(f"--- Finished scrape for {destination} ---")

async def main_multi_destination():
    destinations = ["Paris", "London", "Tokyo"]
    adults = 2
    rooms = 1
    output_dir = Path("scraped_data_multi")
    output_dir.mkdir(exist_ok=True)

    scraper = BookingComScraper(headless=True, cache_enabled=True)
    try:
        tasks = [
            scrape_destination(scraper, dest, adults, rooms, output_dir)
            for dest in destinations
        ]
        await asyncio.gather(*tasks)
    finally:
        await scraper.close()
        print("\nAll multi-destination scraping complete.")

if __name__ == "__main__":
    asyncio.run(main_multi_destination())
```

This will create `scraped_data_multi/paris_hotels.csv`, `scraped_data_multi/london_hotels.csv`, and `scraped_data_multi/tokyo_hotels.csv`.

---

## 📚 API Reference

`ez-rent` is built around a modular architecture, with key functions and classes facilitating the scraping process. This section outlines the main components you'll interact with.

### `BookingComScraper` Class

The primary class for orchestrating web scraping tasks on Booking.com.

```python
class BookingComScraper:
    def __init__(
        self,
        headless: bool = True,
        cache_enabled: bool = False,
        timeout: int = 30000,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Initializes the BookingComScraper.

        Args:
            headless (bool): If True, runs the browser in headless mode (no UI).
            cache_enabled (bool): If True, enables URL caching to avoid redundant requests.
            timeout (int): Default timeout for Playwright actions in milliseconds.
            proxy (Optional[str]): Proxy server URL (e.g., 'http://user:pass@host:port').
            user_agent (Optional[str]): Custom User-Agent string.
        """
    
    async def search_and_collect_urls(
        self,
        destination: str,
        adults: int = 2,
        rooms: int = 1,
        checkin_date: Optional[str] = None, # YYYY-MM-DD
        checkout_date: Optional[str] = None # YYYY-MM-DD
    ) -> List[Dict[str, Any]]:
        """
        Navigates to Booking.com, performs a search, and collects basic information
        and detail page URLs for properties from the search results.

        Args:
            destination (str): The search destination (e.g., "Paris").
            adults (int): Number of adults.
            rooms (int): Number of rooms.
            checkin_date (Optional[str]): Check-in date in 'YYYY-MM-DD' format.
            checkout_date (Optional[str]): Check-out date in 'YYYY-MM-DD' format.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing
                                  basic property info and its detail page URL.
        """

    async def scrape_property_details(
        self,
        property_url: str
    ) -> returns.result.Result[Dict[str, Any], Exception]:
        """
        Scrapes detailed information for a single property from its URL.
        Handles various popups and dynamic content loading.

        Args:
            property_url (str): The URL of the property detail page.

        Returns:
            returns.result.Result[Dict[str, Any], Exception]: A Result object
                containing the property details (Dict) on success, or an
                Exception on failure.
        """

    async def scrape_multiple_property_details(
        self,
        property_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Concurrently scrapes detailed information for multiple properties.

        Args:
            property_list (List[Dict[str, Any]]): A list of dictionaries,
                                                  each containing at least a 'url' key.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing
                                  the detailed information of a scraped property.
        """

    async def close(self):
        """
        Closes the Playwright browser instance.
        """
```

### `save_data_to_csv` Function (Utility)

A utility function (assumed to be available) for persisting scraped data.

```python
from pathlib import Path
from typing import List, Dict, Any

def save_data_to_csv(data: List[Dict[str, Any]], filepath: Path):
    """
    Saves a list of dictionaries to a CSV file.

    Args:
        data (List[Dict[str, Any]]): The list of dictionaries to save.
        filepath (Path): The path to the output CSV file.
    """
```

---

## 🤝 Contributing

We welcome contributions to `ez-rent`! Whether it's reporting bugs, suggesting new features, or submitting code changes, your help is valuable.

### Development Setup

1.  Fork the `ez-rent` repository on GitHub.
2.  Clone your forked repository:
    ```bash
    git clone https://github.com/YOUR_USERNAME/ez-rent.git
    cd ez-rent
    ```
3.  Create a virtual environment and install dependencies:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    playwright install
    ```
4.  Make your changes.

### Testing

While explicit testing commands are not yet provided, ensure your changes integrate well with existing functionality. Run your custom scripts (as shown in [Usage](#-usage) and [Examples](#-examples)) to verify expected behavior.

### Submitting Contributions

1.  Create a new branch for your feature or bug fix: `git checkout -b feature/my-new-feature`.
2.  Commit your changes with a clear and concise message. Follow conventional commits if possible (e.g., `feat: Add new feature`, `fix: Resolve bug`).
3.  Push your branch to your fork: `git push origin feature/my-new-feature`.
4.  Open a Pull Request to the `master` branch of the original `Tenuka22/ez-rent` repository.

We appreciate the effort by Tenuka22 and other contributors to enhance `ez-rent`'s capabilities, as seen in the latest commit, `✨ Enhance Booking.com scraper to fetch full property details`.

---

## 📝 License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2024 Tenuka22

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```