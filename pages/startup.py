"""Startup Manager page."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox
)

from core.theme import ThemeManager
from services.startup_manager import (
    StartupItem, scan_startup_items, disable_startup_item, delete_startup_item
)


class StartupScanWorker(QThread):
    finished = Signal(list)

    def run(self):
        self.finished.emit(scan_startup_items())


class StartupPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.items: List[StartupItem] = []
        self._build_ui()
        self._scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Startup Manager")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        btn = QPushButton("Refresh")
        btn.setObjectName("PrimaryButton")
        btn.clicked.connect(self._scan)
        header.addWidget(btn)
        layout.addLayout(header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Command", "Location", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        bar = QHBoxLayout()
        self.btn_disable = QPushButton("Disable")
        self.btn_disable.clicked.connect(self._disable)
        bar.addWidget(self.btn_disable)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)
        bar.addStretch()
        layout.addLayout(bar)

    def _scan(self):
        self.worker = StartupScanWorker()
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(list)
    def _on_done(self, items: List[StartupItem]):
        self.items = items
        self.table.setRowCount(len(items))
        for i, it in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(it.name))
            self.table.setItem(i, 1, QTableWidgetItem(it.command))
            self.table.setItem(i, 2, QTableWidgetItem(it.location))
            self.table.setItem(i, 3, QTableWidgetItem("Enabled" if it.enabled else "Disabled"))
        self.main.show_toast(f"{len(items)} startup items", "info")

    def _selected(self) -> StartupItem | None:
        rows = set(i.row() for i in self.table.selectedIndexes())
        if not rows:
            return None
        return self.items[min(rows)]

    def _disable(self):
        item = self._selected()
        if not item:
            self.main.show_toast("Select an item", "warning")
            return
        if disable_startup_item(item):
            self.main.show_toast(f"Disabled {item.name}", "success")
            self._scan()
        else:
            self.main.show_toast("Failed to disable (admin rights may be required)", "error")

    def _delete(self):
        item = self._selected()
        if not item:
            return
        if QMessageBox.question(self, "Delete", f"Delete startup entry '{item.name}'?") != QMessageBox.Yes:
            return
        if delete_startup_item(item):
            self.main.show_toast(f"Deleted {item.name}", "success")
            self._scan()
        else:
            self.main.show_toast("Delete failed", "error")
