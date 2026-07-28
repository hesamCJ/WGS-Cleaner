"""Process Manager page."""

from __future__ import annotations

import os
from typing import List

import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QLineEdit
)

from core.theme import ThemeManager


class ProcessesPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(3000)
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Process Manager")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter processes…")
        self.search.textChanged.connect(self._refresh)
        header.addWidget(self.search)
        btn = QPushButton("Refresh")
        btn.clicked.connect(self._refresh)
        header.addWidget(btn)
        layout.addLayout(header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["PID", "Name", "CPU %", "RAM (MB)", "Threads", "Path"])
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table, 1)

        bar = QHBoxLayout()
        self.btn_kill = QPushButton("End Process")
        self.btn_kill.setObjectName("DangerButton")
        self.btn_kill.clicked.connect(lambda: self._kill(False))
        bar.addWidget(self.btn_kill)
        self.btn_force = QPushButton("Force Kill")
        self.btn_force.setObjectName("DangerButton")
        self.btn_force.clicked.connect(lambda: self._kill(True))
        bar.addWidget(self.btn_force)
        self.btn_open = QPushButton("Open Location")
        self.btn_open.clicked.connect(self._open_location)
        bar.addWidget(self.btn_open)
        bar.addStretch()
        layout.addLayout(bar)

    def _refresh(self):
        query = self.search.text().strip().lower()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        rows = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "num_threads", "exe"]):
            try:
                info = proc.info
                name = info.get("name") or ""
                if query and query not in name.lower():
                    continue
                mem = info.get("memory_info")
                mem_mb = mem.rss / (1024 * 1024) if mem else 0
                rows.append((
                    str(info["pid"]),
                    name,
                    f"{info.get('cpu_percent') or 0:.1f}",
                    f"{mem_mb:.1f}",
                    str(info.get("num_threads") or 0),
                    info.get("exe") or "",
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(val))
        self.table.setSortingEnabled(True)

    def _selected_pid(self) -> int | None:
        rows = set(i.row() for i in self.table.selectedIndexes())
        if not rows:
            return None
        item = self.table.item(min(rows), 0)
        return int(item.text()) if item else None

    def _kill(self, force: bool):
        pid = self._selected_pid()
        if pid is None:
            self.main.show_toast("Select a process", "warning")
            return
        try:
            p = psutil.Process(pid)
            name = p.name()
            if QMessageBox.question(
                self, "Confirm", f"{'Force kill' if force else 'End'} {name} (PID {pid})?"
            ) != QMessageBox.Yes:
                return
            if force:
                p.kill()
            else:
                p.terminate()
            self.main.show_toast(f"Terminated {name}", "success")
            self._refresh()
        except Exception as e:
            self.main.show_toast(str(e), "error")

    def _open_location(self):
        rows = set(i.row() for i in self.table.selectedIndexes())
        if not rows:
            return
        path = self.table.item(min(rows), 5).text()
        if path and os.path.isfile(path):
            os.startfile(os.path.dirname(path))
        else:
            self.main.show_toast("Path not available", "warning")
