import sys

from loguru import logger


def setup_logging(level: str, log_format: str) -> None:
    """
        Настраивает loguru: убирает handler по умолчанию и добавляет новый
        с нужным уровнем и форматом (text или json)
    """

    logger.remove()
    if log_format == "json":
        logger.add(sys.stdout, level=level, serialize=True)
    else:
        logger.add(sys.stdout, level=level)
