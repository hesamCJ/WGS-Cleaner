"""Registry Cleaner – scan for broken / unused entries with backup."""

from __future__ import annotations

import logging
import winreg
from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QMessageBox, QCheckBox
)

from services.restore_point import create_restore_point

logger = logging.getLogger("CleanerPro.Registry")


@dataclass
class RegIssue:
    path: str
    name: str
    issue: str
    hive: int
    selected: bool = True


class RegistryScanWorker(QThread):
    finished = Signal(list)
    progress = Signal(str)

    def run(self):
        issues: List[RegIssue] = []
        locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, path in locations:
            self.progress.emit(f"Scanning {path}…")
            try:
                self._scan_key(hive, path, issues, depth=0)
            except Exception as e:
                logger.debug("Scan skip %s: %s", path, e)
        self.finished.emit(issues)

    def _scan_key(self, hive: int, path: str, issues: list, depth: int):
        if depth > 3:
            return
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        except OSError:
            return
        i = 0
        while True:
            try:
                name, value, typ = winreg.EnumValue(key, i)
                i += 1
                if typ in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) and value:
                    val = str(value)
                    if (":\\" in val or val.startswith("%")) and not self._path_exists(val):
                        issues.append(RegIssue(
                            path=path, name=name, issue="Broken path reference", hive=hive
                        ))
            except OSError:
                break
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(key, i)
                i += 1
                self._scan_key(hive, f"{path}\\{sub}", issues, depth + 1)
            except OSError:
                break
        winreg.CloseKey(key)

    @staticmethod
    def _path_exists(val: str) -> bool:
        import os
        try:
            if '"' in val:
                parts = val.split('"')
                candidate = parts[1] if len(parts) > 1 else val
            else:
                candidate = val.split()[0] if val else ""
            expanded = os.path.expandvars(candidate)
            if not expanded:
                return True
            return os.path.exists(expanded)
        except Exception:
            return True


class RegistryPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.issues: List[RegIssue] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Registry Cleaner")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_scan.clicked.connect(self._scan)
        header.addWidget(self.btn_scan)
        self.btn_clean = QPushButton("Fix Selected")
        self.btn_clean.setObjectName("DangerButton")
        self.btn_clean.clicked.connect(self._clean)
        header.addWidget(self.btn_clean)
        layout.addLayout(header)

        self.status = QLabel("Scan the registry for broken entries. A restore point is created before any changes.")
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", "Path", "Value", "Issue"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

    def _scan(self):
        self.progress.setVisible(True)
        self.btn_scan.setEnabled(False)
        self.worker = RegistryScanWorker()
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(list)
    def _on_done(self, issues: list):
        self.progress.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.issues = issues
        self.table.setRowCount(len(issues))
        for i, iss in enumerate(issues):
            cb = QCheckBox()
            cb.setChecked(True)
            self.table.setCellWidget(i, 0, cb)
            self.table.setItem(i, 1, QTableWidgetItem(iss.path))
            self.table.setItem(i, 2, QTableWidgetItem(iss.name))
            self.table.setItem(i, 3, QTableWidgetItem(iss.issue))
        self.status.setText(f"Found {len(issues)} potential issues")
        self.main.show_toast(f"{len(issues)} registry issues", "info")

    def _clean(self):
        selected = []
        for i, iss in enumerate(self.issues):
            w = self.table.cellWidget(i, 0)
            if w and w.isChecked():
                selected.append(iss)
        if not selected:
            self.main.show_toast("Nothing selected", "warning")
            return
        if QMessageBox.warning(
            self, "Confirm",
            f"Fix {len(selected)} registry entries?\nA System Restore Point will be created first.",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        create_restore_point("CleanerPro Registry Clean")
        fixed = 0
        for iss in selected:
            try:
                key = winreg.OpenKey(iss.hive, iss.path, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, iss.name)
                winreg.CloseKey(key)
                fixed += 1
            except OSError as e:
                logger.warning("Could not delete %s\\%s: %s", iss.path, iss.name, e)
        self.main.show_toast(f"Fixed {fixed} entries", "success")
        self._scan()
