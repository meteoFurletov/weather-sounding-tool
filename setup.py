"""
Setup script for the Weather Sounding Tool.
Makes it easier for new users to get started.
"""

import os
import sys
import subprocess
import platform


def main():
    """Set up the Weather Sounding Tool environment"""
    print("=== Weather Sounding Tool Setup ===")
    print("This script will help set up the tool on your system.\n")

    # 1. Check Python version
    print("Checking Python version...")
    python_version = sys.version_info
    if python_version.major < 3 or (
        python_version.major == 3 and python_version.minor < 6
    ):
        print("WARNING: This tool works best with Python 3.6 or newer.")
        print(
            f"Your version: Python {python_version.major}.{python_version.minor}.{python_version.micro}\n"
        )
    else:
        print(
            f"Python version looks good: {python_version.major}.{python_version.minor}.{python_version.micro}\n"
        )

    # 2. Install dependencies
    print("Installing required packages...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("Basic dependencies installed successfully!\n")
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        print(
            "Please try installing them manually using: pip install -r requirements.txt\n"
        )

    # 3. Create data directory
    print("Setting up directories...")
    os.makedirs("data", exist_ok=True)
    print("Created 'data' directory for storing raw HTML files.\n")

    # 4. Attempt to install GUI dependencies
    print("Would you like to install GUI dependencies? (y/n)")
    print("This requires tkinter and additional packages.")
    choice = input("> ").lower()

    if choice.startswith("y"):
        try:
            # Check system for tkinter installation
            system = platform.system().lower()

            if system == "linux":
                print("\nFor Linux, you need to install tkinter separately.")
                print("On Ubuntu/Debian systems, use: sudo apt-get install python3-tk")
                print("On Fedora, use: sudo dnf install python3-tkinter")
                print("After installing tkinter, run: pip install tkcalendar")

            elif system == "darwin":  # macOS
                print("\nFor macOS, you may need to install tkinter separately.")
                print("Try: brew install python-tk")
                print("After that, run: pip install tkcalendar")

            elif system == "windows":
                print("\nFor Windows, tkinter is usually included with Python.")
                print("Installing tkcalendar package...")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "tkcalendar"]
                )

            else:
                print(f"\nUnrecognized system: {system}")
                print("Please install tkinter manually for your system.")
                print("After that, install tkcalendar: pip install tkcalendar")

        except Exception as e:
            print(f"Error setting up GUI dependencies: {e}")
    else:
        print(
            "\nGUI setup skipped. You can still use the simple_tool.py or weather_tool.py directly."
        )

    # 5. Show usage instructions
    print("\n=== Setup complete! ===")
    print("To use the tool:")
    print("1. Command-line version: python simple_tool.py")
    print("2. GUI version (if dependencies installed): python gui.py")
    print("3. Direct script: python weather_tool.py --help")
    print("\nFor more information, see the README.md file.")


if __name__ == "__main__":
    main()
