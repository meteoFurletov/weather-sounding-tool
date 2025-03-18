"""
Logger configuration for the weather tool.
"""

import logging
import warnings

# Suppress pandas FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("weather_tool.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)
