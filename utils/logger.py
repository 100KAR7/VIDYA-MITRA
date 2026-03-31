import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from utils.helpers import load_config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    cfg = _safe_load_config()
    log_dir = os.getenv("VIDYA_LOG_DIR", cfg.get("paths", {}).get("log_dir", "logs/"))
    level_name = os.getenv("VIDYA_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    os.makedirs(log_dir, exist_ok=True)
    file_path = os.path.join(log_dir, f"run_{datetime.now():%Y%m%d}.log")
    file_handler = RotatingFileHandler(file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def _safe_load_config() -> dict:
    try:
        return load_config()
    except Exception:
        return {}
