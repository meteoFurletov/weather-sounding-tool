"""
Автоматическая загрузка и обработка с нового сайта Вайоминга
(``weather.arcc.uwyo.edu``) — «как раньше»: указываешь год, месяц и станцию,
остальное происходит само.

Новый сайт не умеет отдавать данные за месяц одним запросом и работает медленно
(~5 c на срок). Поэтому:

* сначала за один запрос скачивается инвентарь станции за год — из него точно
  известно, какие сроки существуют и с каким источником (``src``) их брать;
* затем скачиваются только существующие сроки, параллельно и с повторами при
  сбоях.

Это и быстрее, и надёжнее, чем перебирать все возможные сроки подряд.
"""

from .fetcher import fetch_inventory, fetch_month, _make_session
from .local_input import process_text
from .logger import logger


def fetch_and_process(
    year,
    months,
    station,
    src="UNKNOWN",
    output_dir=None,
    combined_path="DATA.xlsx",
    max_workers=5,
):
    """Скачать и обработать зондирования за один или несколько месяцев.

    Параметры
    ---------
    year : int
        Год.
    months : int | list[int]
        Месяц или список месяцев (например, ``1`` или ``[1, 2, 3]``).
    station : int
        Номер станции (например, ``26075``).
    src : str
        Источник для запроса инвентаря. По умолчанию ``"UNKNOWN"`` подходит
        почти всегда; точный источник для каждого срока берётся из инвентаря.
    max_workers : int
        Сколько сроков качать одновременно. Значение по умолчанию (5) выбрано
        так, чтобы не перегружать медленный сервер (иначе он начинает обрывать
        соединения по таймауту).

    Возвращает словарь-итог с числом обработанных сроков и списком файлов.
    """
    if isinstance(months, int):
        months = [months]

    session = _make_session(pool_size=max_workers * 2)
    try:
        # Инвентарь за год — один запрос, общий для всех месяцев
        inventory = fetch_inventory(year, station, src=src, session=session)
        if not inventory:
            logger.error(
                f"Не удалось получить список доступных сроков для станции {station} "
                f"за {year} год. Проверьте номер станции и год."
            )
            return {"processed": 0, "failed": 0, "files": []}

        texts = []
        for month in months:
            logger.info(f"Загрузка {year}-{month:02d}, станция {station}...")
            texts.append(
                fetch_month(
                    year,
                    month,
                    station,
                    src=src,
                    max_workers=max_workers,
                    session=session,
                    inventory=inventory,
                )
            )
    finally:
        session.close()

    combined = "\n\n".join(t for t in texts if t)
    if not combined.strip():
        logger.error(
            f"За выбранный период данных нет (станция {station}, {year}, "
            f"месяцы {months})."
        )
        return {"processed": 0, "failed": 0, "files": []}

    return process_text(
        combined, station=station, output_dir=output_dir, combined_path=combined_path
    )
