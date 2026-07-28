"""Path utilities and directory management for Cleaner Pro."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = ASSETS / "icons"
THEMES = ASSETS / "themes"
ANIMATIONS = ASSETS / "animations"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"
DATABASE = ROOT / "database"
TRANSLATIONS = ROOT / "translations"
BACKUP = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CleanerPro" / "Backups"
DATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CleanerPro" / "Data"


def ensure_directories() -> None:
    """Create all required application directories."""
    for d in (LOGS, REPORTS, DATABASE, BACKUP, DATA, ICONS, THEMES):
        d.mkdir(parents=True, exist_ok=True)


def get_log_file() -> Path:
    return LOGS / "cleanerpro.log"


def get_db_path() -> Path:
    return DATABASE / "cleanerpro.db"


def get_backup_dir() -> Path:
    return BACKUP
