"""Centralized logging configuration."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.paths import get_log_file, ensure_directories


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging."""
    ensure_directories()
    log_file = get_log_file()

    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    for h in root.handlers[:]:
        root.removeHandler(h)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Rotating file
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.getLogger("CleanerPro").info("Logging initialized → %s", log_file)
