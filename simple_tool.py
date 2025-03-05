"""
Simple command-line interface for the weather sounding tool.
No GUI dependencies required.
"""

import os
import sys
import subprocess
import argparse


def show_menu():
    """Display the main menu"""
    print("\n===== Weather Sounding Data Tool =====\n")
    print("1. Fetch data from Wyoming database")
    print("2. Process previously fetched data")
    print("3. Fetch and process in one step")
    print("4. View available data files")
    print("5. Exit")

    choice = input("\nEnter your choice (1-5): ")
    return choice


def get_parameters():
    """Get common parameters from user input"""
    # Get year
    while True:
        try:
            year = int(input("Enter year (e.g., 2021): "))
            if 1990 <= year <= 2030:
                break
            print("Year should be between 1990 and 2030.")
        except ValueError:
            print("Please enter a valid year.")

    # Get month range
    while True:
        try:
            start_month = int(input("Enter start month (1-12): "))
            if 1 <= start_month <= 12:
                break
            print("Month should be between 1 and 12.")
        except ValueError:
            print("Please enter a valid month number.")

    # Check if multi-month
    multi_month = input("Process multiple months? (y/n): ").lower() == "y"

    end_month = start_month
    if multi_month:
        while True:
            try:
                end_month = int(input("Enter end month (must be >= start month): "))
                if start_month <= end_month <= 12:
                    break
                print(f"End month should be between {start_month} and 12.")
            except ValueError:
                print("Please enter a valid month number.")

    # Get station ID
    while True:
        try:
            station = int(input("Enter station ID (e.g., 26075 for St. Petersburg): "))
            break
        except ValueError:
            print("Please enter a valid station ID.")

    return year, start_month, end_month, station


def fetch_data():
    """Fetch data from Wyoming database"""
    print("\n--- Fetch Weather Sounding Data ---\n")
    year, start_month, end_month, station = get_parameters()

    cmd = [
        "python",
        "weather_tool.py",
        "--fetch",
        "--year",
        str(year),
        "--month",
        str(start_month),
        "--station",
        str(station),
    ]

    if start_month != end_month:
        cmd.extend(["--end-month", str(end_month)])

    print("\nExecuting:", " ".join(cmd))
    print("This may take a while...")

    subprocess.run(cmd)

    input("\nPress Enter to continue...")


def process_data():
    """Process previously fetched data"""
    print("\n--- Process Weather Sounding Data ---\n")
    year, start_month, end_month, station = get_parameters()

    cmd = [
        "python",
        "weather_tool.py",
        "--process",
        "--year",
        str(year),
        "--month",
        str(start_month),
        "--station",
        str(station),
        "--use-local",
    ]

    if start_month != end_month:
        cmd.extend(["--end-month", str(end_month)])

    print("\nExecuting:", " ".join(cmd))
    print("Processing data...")

    subprocess.run(cmd)

    print(f"\nResults saved in soundings_{year}_{station}/ directory")
    print("Combined analysis saved to DATA.xlsx")

    input("\nPress Enter to continue...")


def fetch_and_process():
    """Fetch and process data in one step"""
    print("\n--- Fetch and Process Weather Sounding Data ---\n")
    year, start_month, end_month, station = get_parameters()

    cmd = [
        "python",
        "weather_tool.py",
        "--year",
        str(year),
        "--month",
        str(start_month),
        "--station",
        str(station),
    ]

    if start_month != end_month:
        cmd.extend(["--end-month", str(end_month)])

    print("\nExecuting:", " ".join(cmd))
    print("Fetching and processing data...")

    subprocess.run(cmd)

    print(f"\nResults saved in soundings_{year}_{station}/ directory")
    print("Combined analysis saved to DATA.xlsx")

    input("\nPress Enter to continue...")


def view_available_data():
    """View available data files"""
    print("\n--- Available Data Files ---\n")

    # Check for HTML data files
    data_dir = "data"
    if os.path.isdir(data_dir):
        html_files = [f for f in os.listdir(data_dir) if f.endswith(".html")]
        if html_files:
            print("Raw HTML data files:")
            for file in sorted(html_files):
                print(f"  - {file}")
        else:
            print("No raw HTML data files found.")
    else:
        print("Data directory not found.")

    # Check for output directories
    soundings_dirs = [d for d in os.listdir() if d.startswith("soundings_")]
    if soundings_dirs:
        print("\nOutput directories:")
        for dir_name in sorted(soundings_dirs):
            files_count = len([f for f in os.listdir(dir_name) if f.endswith(".xlsx")])
            print(f"  - {dir_name} ({files_count} files)")
    else:
        print("\nNo output directories found.")

    # Check for combined file
    if os.path.exists("DATA.xlsx"):
        print("\nCombined analysis file: DATA.xlsx")
    else:
        print("\nNo combined analysis file found.")

    input("\nPress Enter to continue...")


def main():
    """Main function"""
    while True:
        choice = show_menu()

        if choice == "1":
            fetch_data()
        elif choice == "2":
            process_data()
        elif choice == "3":
            fetch_and_process()
        elif choice == "4":
            view_available_data()
        elif choice == "5":
            print("\nExiting. Goodbye!")
            return 0
        else:
            print("\nInvalid choice. Please try again.")


if __name__ == "__main__":
    sys.exit(main())
