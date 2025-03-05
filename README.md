# Weather Sounding Data Processor

This tool processes weather sounding data from the University of Wyoming database. It extracts temperature inversions and saves them as Excel files for analysis.

## Features

- Download weather sounding data from the University of Wyoming
- Handle connection issues by saving raw data locally
- Extract temperature inversions below 1000m altitude
- Generate individual Excel files for each sounding
- Create a combined analysis file with multiple sheets

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/weather-sounding-tool.git
   cd weather-sounding-tool
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. For GUI (optional):
   ```bash
   # On Ubuntu/Debian:
   sudo apt-get install python3-tk
   pip install tkcalendar
   ```

## Usage

### Option 1: Simple Command Line Interface

### Option 4: No Installation - Use Online Demo

For users who don't want to install anything, you can use the online demo:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yourusername/weather-sounding-tool/blob/main/demo.ipynb)

This allows you to:
1. Run the tool directly in your browser
2. Process data from the Wyoming database
3. Download the results to your computer

No installation required!

## Output Files

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

