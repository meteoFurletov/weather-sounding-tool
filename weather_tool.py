"""
Weather Sounding Data Tool

A unified tool for fetching and processing weather sounding data from the University of Wyoming.
This tool handles both fetching raw data and processing it to extract temperature inversions.
"""

import os
import sys
import argparse
import random
import time

# Import components from the weather_tool package
from weather_tool.fetcher import fetch_data
from weather_tool.processor import process_data
from weather_tool.logger import logger


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
