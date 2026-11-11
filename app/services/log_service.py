import logging

from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BASE_DIR / "logs"


def create_logger(request_id: str) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_hour = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name_file = (f"debenture_{date_hour}_{request_id}.log")
    path_log = LOG_DIR / name_file

    logger = logging.getLogger(f"debenture.{request_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.FileHandler(path_log, encoding="utf-8")

    format = logging.Formatter(fmt=("%(asctime)s | %(levelname)s | %(message)s"), datefmt="%Y-%m-%d %H:%M:%S")
    format.converter = lambda *args: (datetime.now(timezone.utc).timetuple())

    handler.setFormatter(format)
    logger.addHandler(handler)

    register_log(logger, f"Logger iniciado. Request ID: {request_id}")
    return logger


def register_log(logger: logging.Logger, message: str, level: str = "INFO") -> None:
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    level_logging = levels.get(level.upper(), logging.INFO)
    logger.log(level_logging, message)


def finalize_logger(logger: logging.Logger) -> None:
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()