"""
Functions for fetching weather sounding data from the University of Wyoming.
"""

import os
import requests
from bs4 import BeautifulSoup
from .logger import logger


def get_days_in_month(year, month):
    """Return the number of days in a given month and year."""
    import calendar

    return calendar.monthrange(year, month)[1]


def fetch_data(year, month, station, output_dir="data"):
    """Fetch weather sounding data and save to a local file"""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get the number of days in the month
    num_days = get_days_in_month(year, month)

    # Construct URL with proper date range
    url = (
        f"http://weather.uwyo.edu/cgi-bin/sounding?region=europe&"
        f"TYPE=TEXT%3ALIST&YEAR={year}&MONTH={month:02d}&"
        f"FROM=0100&TO={num_days:02d}12&STNM={station}"
    )
    logger.info(f"Fetching data from: {url}")

    # Add headers to make request more like a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        # Save raw response
        output_file = f"{output_dir}/response_{year}_{month:02d}_{station}.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.text)

        # Check content
        soup = BeautifulSoup(response.content, "html.parser")
        h2_count = len(soup.find_all("h2"))
        pre_count = len(soup.find_all("pre"))

        logger.info(f"Saved raw HTML to {output_file} ({h2_count} soundings)")
        return output_file

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None
