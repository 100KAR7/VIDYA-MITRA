import logging
import os
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    os.makedirs("logs", exist_ok=True)
    file_path = os.path.join("logs", f"run_{datetime.now():%Y%m%d}.log")
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
"""
utils/logger.py
PURPOSE : Central logging — writes to console AND a daily log file.

USAGE in any file:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("message")
    log.warning("message")
    log.error("message")
"""

import logging
import os
import sys
from datetime import datetime


def get_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already set up, don't add duplicate handlers

    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        fmt    = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt= "%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler — one file per day
    today = datetime.now().strftime("%Y%m%d")
    fh    = logging.FileHandler(f"{log_dir}/run_{today}.log", mode="a")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.propagate = False
    return logger
