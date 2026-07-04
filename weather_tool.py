"""
Weather Sounding Data Tool

Автоматически скачивает и обрабатывает данные метеорологических зондирований с
сайта Университета Вайоминга (новый сервер weather.arcc.uwyo.edu) и извлекает
температурные инверсии.

Примеры:
    python weather_tool.py --year 2025 --month 1 --station 26075
    python weather_tool.py --year 2025 --month 1 --end-month 3 --station 26075
    python weather_tool.py --fetch --year 2025 --month 1 --station 26075   # только скачать
    python weather_tool.py --process --year 2025 --month 1 --station 26075 # обработать скачанное
"""

import sys
import argparse

from weather_tool.online import fetch_and_process
from weather_tool.fetcher import fetch_inventory, fetch_month, _make_session
from weather_tool.local_input import process_files, process_text, read_document_text
from weather_tool.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Weather Sounding Data Tool")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--fetch", action="store_true", help="Только скачать данные, не обрабатывать"
    )
    group.add_argument(
        "--process",
        action="store_true",
        help="Только обработать ранее скачанные данные (из папки data/)",
    )

    parser.add_argument("--year", type=int, default=2025, help="Год")
    parser.add_argument(
        "--month",
        type=int,
        default=1,
        help="Месяц (1-12) или начальный месяц, если задан --end-month",
    )
    parser.add_argument(
        "--end-month", type=int, help="Конечный месяц диапазона (включительно)"
    )
    parser.add_argument("--station", type=int, default=26075, help="Номер станции")
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Сколько сроков качать одновременно (по умолчанию 5)",
    )
    parser.add_argument(
        "--from-file",
        nargs="+",
        metavar="PATH",
        help="Запасной режим: обработать локальные файлы (.docx/.txt/.html) вместо загрузки с сайта",
    )

    args = parser.parse_args()

    months = list(range(args.month, (args.end_month or args.month) + 1))

    # --- Запасной режим: обработка из локальных файлов ---
    if args.from_file:
        print("\n=== Weather Sounding Data Tool (локальные файлы) ===")
        print(f"Файлы: {args.from_file}\nСтанция: {args.station}\n")
        summary = process_files(args.from_file, station=args.station)
        _print_summary(summary, args)
        return 0

    print("\n=== Weather Sounding Data Tool ===")
    print(f"Год: {args.year}")
    print(f"Месяцы: {months}")
    print(f"Станция: {args.station}")

    # --- Только обработка ранее скачанных файлов ---
    if args.process:
        print("Режим: только обработка (из папки data/)\n")
        texts = []
        for month in months:
            path = f"data/response_{args.year}_{month:02d}_{args.station}.txt"
            try:
                texts.append(read_document_text(path))
                logger.info(f"Загружено из {path}")
            except FileNotFoundError:
                logger.error(f"Нет скачанного файла: {path} (сначала запустите --fetch)")
        summary = process_text("\n\n".join(texts), station=args.station)
        _print_summary(summary, args)
        return 0

    # --- Только скачивание ---
    if args.fetch:
        print("Режим: только скачивание (в папку data/)\n")
        session = _make_session(pool_size=args.workers * 2)
        try:
            inventory = fetch_inventory(args.year, args.station, session=session)
            for month in months:
                fetch_month(
                    args.year,
                    month,
                    args.station,
                    max_workers=args.workers,
                    session=session,
                    inventory=inventory,
                )
        finally:
            session.close()
        print("\nСкачивание завершено. Данные — в папке data/.")
        return 0

    # --- По умолчанию: скачать и обработать ---
    print("Режим: скачать и обработать\n")
    summary = fetch_and_process(
        args.year, months, args.station, max_workers=args.workers
    )
    _print_summary(summary, args)
    return 0


def _print_summary(summary, args):
    print("\nИтоги:")
    print(f"- Сроков с инверсиями сохранено: {summary['processed']}")
    print(f"- Сроков без инверсий/пропущено: {summary['failed']}")
    print(f"- Отдельные файлы: soundings_{args.year}_{args.station}/")
    print("- Сводный файл: DATA.xlsx")


if __name__ == "__main__":
    sys.exit(main())
