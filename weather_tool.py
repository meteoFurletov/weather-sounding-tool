"""
Weather Sounding Data Tool

A unified tool for fetching and processing weather sounding data from the University of Wyoming.
This tool handles both fetching raw data and processing it to extract temperature inversions.
"""

import os
import sys
import argparse
import requests
import pandas as pd
import numpy as np
import logging
import warnings
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime

# Suppress pandas FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("weather_tool.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# --- DATA FETCHING FUNCTIONS ---


def fetch_data(year, month, station, output_dir="data"):
    """Fetch weather sounding data and save to a local file"""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Construct URL
    url = (
        f"http://weather.uwyo.edu/cgi-bin/sounding?region=europe&"
        f"TYPE=TEXT%3ALIST&YEAR={year}&MONTH={month:02d}&"
        f"FROM=0100&TO=3112&STNM={station}"
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


# --- PROCESSING FUNCTIONS ---


def extract_soundings_from_html(html_content):
    """Extract individual soundings from HTML content"""

    soup = BeautifulSoup(html_content, "html.parser")

    # Find all h2 and pre tags
    h2_tags = soup.find_all("h2")
    pre_tags = soup.find_all("pre")

    if len(h2_tags) == 0 or len(pre_tags) == 0:
        logger.error("No valid data found in HTML")
        return []

    # Handle the case where there are twice as many pre tags as h2 tags
    if len(pre_tags) == 2 * len(h2_tags):
        logger.info(
            "Found twice as many pre tags as h2 tags. Using every other pre tag."
        )
        pre_tags = pre_tags[::2]  # Take every other pre tag
    elif len(h2_tags) != len(pre_tags):
        logger.error(
            f"Mismatch between tag counts: {len(h2_tags)} h2 vs {len(pre_tags)} pre"
        )
        return []

    # Extract soundings
    soundings = []
    for h2, pre in zip(h2_tags, pre_tags):
        try:
            # Extract datetime with regex
            import re

            date_match = re.search(
                r"(\d{2})Z\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", h2.text
            )
            if date_match:
                hour, day, month_name, year = date_match.groups()
                time_str = f"{hour}{day}{month_name}{year}"
                time = pd.to_datetime(time_str, format="%H%d%b%Y")
                soundings.append((pre.text, time))
        except Exception as e:
            logger.error(f"Error processing sounding: {e}")

    logger.info(f"Extracted {len(soundings)} soundings")
    return soundings


def process_sounding(raw_text, time):
    """Process a single sounding to extract temperature inversions"""

    # Parse the raw text into rows
    results = []
    for line in raw_text.split("\n")[1:-1]:  # Skip header and footer
        if "--" not in line:
            row = [line[i : i + 7].strip() for i in range(0, len(line), 7)]
            results.append(row)

    if len(results) < 2:
        return None, None

    # Create DataFrame
    df = pd.DataFrame(results)
    df.columns = df.iloc[0]
    df = df[2:].reset_index(drop=True)  # Skip header rows

    # Convert to numeric
    try:
        df = df.replace("", np.nan).astype(float)
        df["SKNT"] = (df["SKNT"] * 0.51444444444444).round(2)  # Convert to m/s
    except ValueError as e:
        return None, None

    # Detect temperature inversions (where temperature increases with height)
    df_inverse = pd.DataFrame(columns=df.columns)
    i = 0
    while i < len(df) - 1:
        if df["TEMP"].iloc[i + 1] > df["TEMP"].iloc[i]:
            df_inverse = pd.concat([df_inverse, df.iloc[i : i + 2]])
            i += 2
        else:
            i += 1

    if df_inverse.empty:
        return df, pd.DataFrame()

    df_inverse = df_inverse.reset_index(drop=True)

    # Filter inversions below 1000m and add metadata
    df_inverse = df_inverse[df_inverse["HGHT"] <= 1000].drop_duplicates()

    if not df_inverse.empty:
        df_inverse["date"] = time
        df_inverse["ΔT"] = df_inverse["TEMP"].iloc[-1] - df_inverse["TEMP"].iloc[0]
        df_inverse["ΔH"] = df_inverse["HGHT"].iloc[-1] - df_inverse["HGHT"].iloc[0]
        df_inverse["HL"] = df_inverse["HGHT"].iloc[0]
        df_inverse["TL"] = df_inverse["TEMP"].iloc[0]
        df_inverse["Ground"] = 1 if df_inverse["HGHT"].iloc[0] == 72 else 0
        df_inverse["Night"] = 1 if time.hour == 0 else 0
        df_inverse["Day"] = 1 if time.hour == 12 else 0

        # Filter out zero height difference
        if df_inverse["ΔH"].iloc[0] == 0:
            return df, pd.DataFrame()

    return df, df_inverse


def process_data(year, months, station, use_local_files=True):
    """Process data for specified months and save results"""

    # Create output directory for individual files
    output_dir = f"soundings_{year}_{station}"
    os.makedirs(output_dir, exist_ok=True)

    summary = {"processed": 0, "failed": 0, "files": []}
    all_inversions = []

    for month in months:
        # Load data from file or fetch if needed
        html_content = None

        if use_local_files:
            # Try to load from local file
            search_paths = [
                f"data/response_{year}_{month:02d}_{station}.html",
                f"test_results/response_{year}_{month:02d}_{station}.html",
            ]

            for path in search_paths:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    logger.info(f"Loaded data from {path}")
                    break

        # Fetch if no local file found or not using local files
        if html_content is None:
            if not use_local_files:
                logger.info(f"Fetching data for {year}-{month:02d}")
                file_path = fetch_data(year, month, station)
                if file_path and os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
            else:
                logger.error(f"No local file found for {year}-{month:02d}")
                continue

        # Process the soundings
        soundings = extract_soundings_from_html(html_content)

        for raw_text, time in soundings:
            _, df_inverse = process_sounding(raw_text, time)

            if df_inverse is not None and not df_inverse.empty:
                summary["processed"] += 1

                # Prepare data for saving
                single_data = df_inverse.drop(
                    [
                        "PRES",
                        "HGHT",
                        "TEMP",
                        "DWPT",
                        "RELH",
                        "MIXR",
                        "DRCT",
                        "SKNT",
                        "THTA",
                        "THTE",
                        "THTV",
                    ],
                    axis=1,
                    errors="ignore",
                )
                single_data = single_data[single_data["ΔT"] > 0].drop_duplicates()

                # Save individual file
                timestamp = time.strftime("%Y%m%d_%H%M")
                filename = f"{output_dir}/DATA_{timestamp}.xlsx"

                with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
                    single_data.to_excel(writer, sheet_name="inversion_data")

                logger.info(f"Saved: {filename}")
                summary["files"].append(filename)
                all_inversions.append(single_data)
            else:
                summary["failed"] += 1

    # Create combined file
    if all_inversions:
        create_combined_file(all_inversions, year, months)

    return summary


def create_combined_file(all_inversions, year, months):
    """Create a combined Excel file with multiple analysis sheets"""

    # Combine all inversions
    combined_data = pd.concat(all_inversions, ignore_index=True)

    # Create full date range
    start_date = f"{year}-{months[0]:02d}-01"
    end_month = months[-1]
    end_day = 31  # Using 31 for all months as pandas will auto-adjust
    end_date = f"{year}-{end_month:02d}-{end_day}"

    dates = pd.date_range(start=start_date, end=end_date, freq="12H")
    dates_df = pd.DataFrame({"date": dates})

    # Merge with full date range
    data_full = dates_df.merge(combined_data, on="date", how="left")

    # Create analysis subsets
    subsets = {
        "df_full": data_full,
        "df_ground": data_full[data_full["Ground"] == 1],
        "df_not_ground": data_full[data_full["Ground"] == 0],
        "df_day": data_full[data_full["Day"] == 1],
        "df_night": data_full[data_full["Night"] == 1],
        "df_ground_night": data_full[
            (data_full["Ground"] == 1) & (data_full["Night"] == 1)
        ],
        "df_ground_day": data_full[
            (data_full["Ground"] == 1) & (data_full["Day"] == 1)
        ],
        "df_not_ground_night": data_full[
            (data_full["Ground"] == 0) & (data_full["Night"] == 1)
        ],
        "df_not_ground_day": data_full[
            (data_full["Ground"] == 0) & (data_full["Day"] == 1)
        ],
    }

    # Save to Excel file
    with pd.ExcelWriter("DATA.xlsx", engine="xlsxwriter") as writer:
        for name, df in subsets.items():
            df.to_excel(writer, sheet_name=name, index=False)

    logger.info(f"Created combined file DATA.xlsx with {len(subsets)} analysis sheets")


def main():
    parser = argparse.ArgumentParser(description="Weather Sounding Data Tool")

    # Main mode options
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--fetch", action="store_true", help="Only fetch data, don't process"
    )
    group.add_argument(
        "--process", action="store_true", help="Only process existing data"
    )

    # Common parameters
    parser.add_argument("--year", type=int, default=2021, help="Year to process")
    parser.add_argument(
        "--month",
        type=int,
        default=1,
        help="Month (1-12) or start month if end-month provided",
    )
    parser.add_argument("--end-month", type=int, help="End month for range (inclusive)")
    parser.add_argument("--station", type=int, default=26075, help="Station ID")

    args = parser.parse_args()

    # Default is to do both fetch and process if neither flag is specified
    do_fetch = args.fetch or not (args.fetch or args.process)
    do_process = args.process or not (args.fetch or args.process)

    # Process a range of months
    end_month = args.end_month if args.end_month else args.month
    months = list(range(args.month, end_month + 1))

    # Header
    print("\n=== Weather Sounding Data Tool ===")
    print(f"Year: {args.year}")
    print(f"Months: {months}")
    print(f"Station: {args.station}")
    print(
        f"Mode: {'Fetch & Process' if do_fetch and do_process else 'Fetch Only' if do_fetch else 'Process Only'}\n"
    )

    # Fetch data if needed
    if do_fetch:
        print("Fetching data...")
        os.makedirs("data", exist_ok=True)

        for month in months:
            print(f"Fetching {args.year}-{month:02d}...")
            fetch_data(args.year, month, args.station)
            if month < months[-1]:  # Add delay between requests
                delay = random.uniform(2, 5)
                time.sleep(delay)

        print("Data fetching completed!\n")

    # Process data if needed
    if do_process:
        print("Processing data...")
        summary = process_data(args.year, months, args.station, use_local_files=True)

        print("\nProcessing summary:")
        print(f"- Successfully processed: {summary['processed']} soundings")
        print(f"- Failed to process: {summary['failed']} soundings")
        print(f"- Individual files in: soundings_{args.year}_{args.station}/")
        print("- Combined file: DATA.xlsx")

    return 0


if __name__ == "__main__":
    sys.exit(main())
