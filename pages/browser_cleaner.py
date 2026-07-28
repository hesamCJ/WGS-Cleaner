"""Browser cache / history / cookies cleaner for major browsers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Dict

import humanize
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QGroupBox, QProgressBar, QMessageBox
)

from core.theme import ThemeManager


def _browser_paths() -> Dict[str, Dict[str, Path]]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))
    return {
        "Chrome": {
            "Cache": local / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
            "Code Cache": local / "Google" / "Chrome" / "User Data" / "Default" / "Code Cache",
            "Cookies": local / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies",
            "History": local / "Google" / "Chrome" / "User Data" / "Default" / "History",
            "Sessions": local / "Google" / "Chrome" / "User Data" / "Default" / "Sessions",
        },
        "Edge": {
            "Cache": local / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            "Code Cache": local / "Microsoft" / "Edge" / "User Data" / "Default" / "Code Cache",
            "Cookies": local / "Microsoft" / "Edge" / "User Data" / "Default" / "Network" / "Cookies",
            "History": local / "Microsoft" / "Edge" / "User Data" / "Default" / "History",
            "Sessions": local / "Microsoft" / "Edge" / "User Data" / "Default" / "Sessions",
        },
        "Firefox": {
            "Cache": local / "Mozilla" / "Firefox" / "Profiles",
            "Cookies": roaming / "Mozilla" / "Firefox" / "Profiles",
        },
        "Opera": {
            "Cache": local / "Opera Software" / "Opera Stable" / "Cache",
            "History": local / "Opera Software" / "Opera Stable" / "History",
        },
        "Brave": {
            "Cache": local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cache",
            "Cookies": local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Network" / "Cookies",
            "History": local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "History",
        },
    }


def _folder_size(p: Path) -> int:
    total = 0
    if not p.exists():
        return 0
    try:
        if p.is_file():
            return p.stat().st_size
        for root, _, files in os.walk(p):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


class BrowserScanWorker(QThread):
    finished = Signal(dict)
    progress = Signal(str)

    def run(self):
        result = {}
        for browser, paths in _browser_paths().items():
            result[browser] = {}
            for name, path in paths.items():
                self.progress.emit(f"Scanning {browser} – {name}")
                result[browser][name] = {"path": path, "size": _folder_size(path)}
        self.finished.emit(result)


class BrowserCleanerPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.data: dict = {}
        self.checks: Dict[str, QCheckBox] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Browser Cleaner")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_scan.clicked.connect(self._scan)
        header.addWidget(self.btn_scan)
        self.btn_clean = QPushButton("Clean Selected")
        self.btn_clean.setObjectName("DangerButton")
        self.btn_clean.clicked.connect(self._clean)
        header.addWidget(self.btn_clean)
        layout.addLayout(header)

        self.status = QLabel("Click Scan to analyze browser data.")
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.groups_layout = QVBoxLayout()
        layout.addLayout(self.groups_layout)
        layout.addStretch()

    def _scan(self):
        self.progress.setVisible(True)
        self.btn_scan.setEnabled(False)
        self.worker = BrowserScanWorker()
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(dict)
    def _on_done(self, data: dict):
        self.progress.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.data = data
        # Clear previous
        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.checks.clear()

        for browser, items in data.items():
            total = sum(v["size"] for v in items.values())
            if total == 0:
                continue
            group = QGroupBox(f"{browser} – {humanize.naturalsize(total)}")
            v = QVBoxLayout(group)
            for name, info in items.items():
                if info["size"] == 0:
                    continue
                cb = QCheckBox(f"{name} ({humanize.naturalsize(info['size'])})")
                cb.setChecked(name in ("Cache", "Code Cache"))
                key = f"{browser}|{name}"
                self.checks[key] = cb
                v.addWidget(cb)
            self.groups_layout.addWidget(group)
        self.status.setText("Scan complete")
        self.main.show_toast("Browser scan finished", "success")

    def _clean(self):
        to_clean = []
        for key, cb in self.checks.items():
            if cb.isChecked():
                browser, name = key.split("|", 1)
                info = self.data.get(browser, {}).get(name)
                if info:
                    to_clean.append(info["path"])
        if not to_clean:
            self.main.show_toast("Nothing selected", "warning")
            return
        if QMessageBox.question(
            self, "Confirm",
            "Close all browsers first, then confirm clean.\nContinue?"
        ) != QMessageBox.Yes:
            return
        freed = 0
        for p in to_clean:
            try:
                size = _folder_size(p)
                if p.is_file():
                    p.unlink(missing_ok=True)
                else:
                    shutil.rmtree(p, ignore_errors=True)
                    p.mkdir(parents=True, exist_ok=True)
                freed += size
            except Exception:
                pass
        self.main.show_toast(f"Freed {humanize.naturalsize(freed)}", "success")
        self._scan()
