"""
Weather Sounding Data Tool

A unified tool for fetching and processing weather sounding data from the University of Wyoming.
This tool handles both fetching raw data and processing it to extract temperature inversions.
"""

from .fetcher import (
    fetch_data,
    fetch_sounding,
    fetch_month,
    fetch_inventory,
    get_days_in_month,
    DEFAULT_HOURS,
    ALL_HOURS,
)
from .processor import (
    process_data,
    process_sounding,
    detect_inversions,
    extract_soundings_from_html,
    create_combined_file,
)
from .local_input import (
    process_files,
    process_text,
    read_document_text,
    extract_soundings_from_text,
    build_combined_file,
)
from .online import fetch_and_process

__all__ = [
    # Автозагрузка с нового сайта Вайоминга (основной способ)
    "fetch_and_process",
    "fetch_inventory",
    "fetch_sounding",
    "fetch_month",
    "DEFAULT_HOURS",
    "ALL_HOURS",
    # Разбор и обработка
    "process_text",
    "process_data",
    "process_sounding",
    "detect_inversions",
    "extract_soundings_from_html",
    "extract_soundings_from_text",
    "create_combined_file",
    "build_combined_file",
    # Ручной ввод из файла (запасной способ)
    "process_files",
    "read_document_text",
    # Прочее / устаревшее
    "fetch_data",
    "get_days_in_month",
]
