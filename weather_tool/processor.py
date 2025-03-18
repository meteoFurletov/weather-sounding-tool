"""
Functions for processing weather sounding data and extracting temperature inversions.
"""

import os
import pandas as pd
import numpy as np
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime
from .logger import logger
from .fetcher import fetch_data
import calendar


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

    # Improved inversion detection algorithm
    inversions = []
    i = 0

    while i < len(df) - 1:
        # Look for a point where temperature starts increasing with height
        if df["TEMP"].iloc[i + 1] > df["TEMP"].iloc[i]:
            inversion_start = i
            j = i + 1

            # Continue until temperature stops increasing or we reach the end
            while j < len(df) - 1 and df["TEMP"].iloc[j + 1] >= df["TEMP"].iloc[j]:
                j += 1

            inversion_end = j

            # Only consider valid inversions (must include at least 2 points)
            if inversion_end > inversion_start:
                inversion_data = df.iloc[inversion_start : inversion_end + 1].copy()

                # Calculate metadata for this inversion layer
                delta_t = (
                    inversion_data["TEMP"].iloc[-1] - inversion_data["TEMP"].iloc[0]
                )
                delta_h = (
                    inversion_data["HGHT"].iloc[-1] - inversion_data["HGHT"].iloc[0]
                )

                # Only add if there's a height difference and positive temperature change
                if delta_h > 0 and delta_t > 0:
                    inversion_data["date"] = time
                    inversion_data["ΔT"] = delta_t
                    inversion_data["ΔH"] = delta_h
                    inversion_data["HL"] = inversion_data["HGHT"].iloc[0]
                    inversion_data["TL"] = inversion_data["TEMP"].iloc[0]
                    inversion_data["Ground"] = (
                        1 if inversion_data["HGHT"].iloc[0] <= 100 else 0
                    )
                    inversion_data["Night"] = 1 if time.hour == 0 else 0
                    inversion_data["Day"] = 1 if time.hour == 12 else 0

                    inversions.append(inversion_data)

            # Continue from the end of this inversion
            i = inversion_end

        i += 1

    # Combine all found inversions if any
    if inversions:
        df_inverse = pd.concat(inversions, ignore_index=True)
        # Filter inversions below 1000m
        df_inverse = df_inverse[df_inverse["HGHT"] <= 1000].drop_duplicates()
    else:
        df_inverse = pd.DataFrame()

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
    end_day = calendar.monthrange(year, end_month)[1]
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
