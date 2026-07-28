#!/usr/bin/env python3
"""
Cleaner Pro - Production-Ready Windows Optimization Suite
Main entry point.
"""

from __future__ import annotations

import sys
import os
import logging
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QFont, QIcon

from core.app import CleanerProApp
from core.logger import setup_logging
from utils.paths import ensure_directories


def main() -> int:
    """Application entry point."""
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    # Ensure required directories exist
    ensure_directories()

    # Logging
    setup_logging()
    logger = logging.getLogger("CleanerPro")
    logger.info("Starting Cleaner Pro")

    app = QApplication(sys.argv)
    app.setApplicationName("Cleaner Pro")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("CleanerPro")
    app.setOrganizationDomain("cleanerpro.local")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Application icon
    icon_path = ROOT / "assets" / "icons" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Launch main window
    window = CleanerProApp()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
