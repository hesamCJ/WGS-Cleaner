"""SQLite persistence for settings, scan history and reports."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.paths import get_db_path, ensure_directories


class Database:
    def __init__(self, path: Optional[Path] = None):
        ensure_directories()
        self.path = path or get_db_path()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    freed_bytes INTEGER DEFAULT 0,
                    items_count INTEGER DEFAULT 0,
                    details TEXT
                );
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    title TEXT,
                    html_path TEXT,
                    pdf_path TEXT,
                    summary TEXT
                );
            """)

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if row is None:
                return default
            try:
                return json.loads(row["value"])
            except Exception:
                return row["value"]

    def set_setting(self, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )

    def add_scan_history(
        self,
        scan_type: str,
        freed_bytes: int = 0,
        items_count: int = 0,
        details: Optional[dict] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO scan_history
                   (scan_type, started_at, finished_at, freed_bytes, items_count, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (scan_type, now, now, freed_bytes, items_count, json.dumps(details or {})),
            )

    def recent_scans(self, limit: int = 20) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM scan_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
