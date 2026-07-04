"""
Functions for fetching weather sounding data from the University of Wyoming.

The archive migrated (2025) to ``weather.arcc.uwyo.edu`` and now serves only one
observation time ("срок") per request — there is no monthly or date-range
download anymore, and each request is slow (~5 s server-side).

:func:`fetch_month` restores automatic loading efficiently:

1. It first downloads the station's **inventory for the year** in a single
   request. The inventory lists every sounding that actually exists, as direct
   links carrying the exact ``datetime`` and the correct ``src`` for that
   station (e.g. ``FM35``). This means we never waste requests on empty срок
   slots and never have to guess ``src``.
2. Then it downloads only the soundings that exist, in parallel (a small thread
   pool) with automatic retries, and stitches them together.

The legacy :func:`fetch_data` (old monthly URL) is kept unchanged as a fallback.
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

try:  # urllib3 ships with requests; guard just in case
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    Retry = None

from .logger import logger

# New single-sounding endpoint (weather.arcc.uwyo.edu)
NEW_SITE_URL = "https://weather.arcc.uwyo.edu/wsgi/sounding"

# Standard synoptic radiosonde times (00 and 12 UTC), kept for reference/back-compat.
DEFAULT_HOURS = (0, 12)
ALL_HOURS = (0, 3, 6, 9, 12, 15, 18, 21)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# The server is slow per request; give it room but keep a connect cap.
REQUEST_TIMEOUT = (15, 75)  # (connect, read) seconds

# Links inside the INVENTORY page, e.g.
#   href="/wsgi/sounding?src=FM35&datetime=2025-01-03 12:00:00&id=26075&type=TEXT:LIST"
_INV_LINK_RE = re.compile(
    r'href="/wsgi/sounding\?src=([^&"]+)&datetime='
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})&id=(\d+)&type=TEXT:LIST"'
)


def get_days_in_month(year, month):
    """Return the number of days in a given month and year."""
    import calendar

    return calendar.monthrange(year, month)[1]


def _make_session(pool_size=8):
    """A requests Session with keep-alive and automatic retries/backoff."""
    session = requests.Session()
    session.headers.update(HEADERS)
    if Retry is not None:
        retry = Retry(
            total=4,
            connect=4,
            read=4,
            status=3,
            backoff_factor=1.5,  # waits 0, 1.5, 3, 6 s between attempts
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(
            max_retries=retry, pool_connections=pool_size, pool_maxsize=pool_size
        )
    else:  # pragma: no cover
        adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_inventory(year, station, src="UNKNOWN", session=None):
    """Download the station's inventory for a whole year in one request.

    Returns a list of ``(datetime_str, src)`` for every sounding that exists,
    e.g. ``("2025-01-03 12:00:00", "FM35")``. Empty on failure.
    """
    close = session is None
    if session is None:
        session = _make_session()
    try:
        params = {
            "datetime": f"{year:04d}-01-01 00:00:00",
            "id": station,
            "type": "INVENTORY",
            "src": src,
        }
        try:
            response = session.get(
                NEW_SITE_URL, params=params, timeout=(15, 120)
            )
        except Exception as exc:
            logger.error(f"Не удалось получить инвентарь за {year}: {exc}")
            return []
        if response.status_code != 200:
            logger.error(f"Инвентарь за {year}: HTTP {response.status_code}")
            return []
        found = [(dt, src_) for src_, dt, _id in _INV_LINK_RE.findall(response.text)]
        logger.info(f"Инвентарь {station} за {year}: доступно сроков — {len(found)}")
        return found
    finally:
        if close:
            session.close()


def _fetch_one(session, datetime_str, station, src):
    """Fetch one sounding as plain text, or None if unavailable."""
    params = {
        "datetime": datetime_str,
        "id": station,
        "type": "TEXT:LIST",
        "src": src,
    }
    try:
        response = session.get(NEW_SITE_URL, params=params, timeout=REQUEST_TIMEOUT)
    except Exception as exc:
        logger.warning(f"Ошибка запроса {datetime_str}: {exc}")
        return None
    if response.status_code != 200:
        return None
    text = response.text
    if "<pre" not in text.lower() or "Unable to retrieve" in text:
        return None
    return BeautifulSoup(text, "html.parser").get_text("\n")


def fetch_sounding(year, month, day, hour, station, src="UNKNOWN", session=None):
    """Fetch a single sounding (one срок) from the new Wyoming site.

    Convenience wrapper around :func:`_fetch_one`. Returns plain text or None.
    """
    close = session is None
    if session is None:
        session = _make_session()
    try:
        dt = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:00:00"
        return _fetch_one(session, dt, station, src)
    finally:
        if close:
            session.close()


def fetch_month(
    year,
    month,
    station,
    src="UNKNOWN",
    output_dir="data",
    max_workers=5,
    save=True,
    session=None,
    inventory=None,
):
    """Fetch every available sounding for a month from the new Wyoming site.

    Uses the yearly inventory to request only the sroks that actually exist, in
    parallel with retries. Pass a prefetched ``inventory`` (list of
    ``(datetime, src)``) to avoid re-downloading it for each month of a range.
    Returns the combined plain text (empty if the month has no data).
    """
    close = session is None
    if session is None:
        session = _make_session(pool_size=max_workers * 2)
    try:
        if inventory is None:
            inventory = fetch_inventory(year, station, src=src, session=session)

        prefix = f"{year:04d}-{month:02d}"
        slots = [(dt, s) for dt, s in inventory if dt.startswith(prefix)]

        if not slots:
            logger.warning(f"{prefix}: в инвентаре нет доступных сроков.")
            return ""

        logger.info(
            f"{prefix}: качаю {len(slots)} сроков "
            f"(≈{len(slots) * 6 // max_workers} c, сервер медленный)..."
        )

        results = {}
        total = len(slots)
        done = 0
        step = max(1, total // 5)  # прогресс примерно каждые 20%
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(_fetch_one, session, dt, station, s): dt
                for dt, s in slots
            }
            for future in as_completed(futures):
                dt = futures[future]
                text = future.result()
                if text:
                    results[dt] = text
                done += 1
                if done % step == 0 or done == total:
                    logger.info(f"{prefix}: {done}/{total} сроков загружено")

        missing = [dt for dt, _ in slots if dt not in results]
        if missing:
            logger.warning(
                f"{prefix}: не удалось получить {len(missing)} из {len(slots)} "
                f"сроков (пропущены): {', '.join(missing)}"
            )
        logger.info(f"{prefix}: получено {len(results)} из {len(slots)} сроков.")

        blocks = [results[dt] for dt in sorted(results)]
        combined = "\n\n".join(blocks)

        if save and combined:
            os.makedirs(output_dir, exist_ok=True)
            out_file = f"{output_dir}/response_{year}_{month:02d}_{station}.txt"
            with open(out_file, "w", encoding="utf-8") as handle:
                handle.write(combined)
            logger.info(f"Сохранено в {out_file}")

        return combined
    finally:
        if close:
            session.close()


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
