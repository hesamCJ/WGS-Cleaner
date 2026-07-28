"""Temporary Cleaner page."""

from __future__ import annotations

import logging
from typing import List

import humanize
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QCheckBox, QMessageBox
)

from core.theme import ThemeManager
from services.temp_cleaner import get_clean_targets, scan_targets, clean_targets, CleanTarget

logger = logging.getLogger("CleanerPro.TempPage")


class ScanThread(QThread):
    finished = Signal(list)
    progress = Signal(str)

    def run(self):
        targets = get_clean_targets()
        scanned = scan_targets(targets, lambda m: self.progress.emit(m))
        self.finished.emit(scanned)


class CleanThread(QThread):
    finished = Signal(int, int, list)  # freed, errors, messages
    progress = Signal(str)

    def __init__(self, targets: List[CleanTarget]):
        super().__init__()
        self.targets = targets

    def run(self):
        freed, errors, msgs = clean_targets(
            self.targets, use_recycle_bin=True, progress_cb=lambda m: self.progress.emit(m)
        )
        self.finished.emit(freed, errors, msgs)


class TempCleanerPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.theme = ThemeManager()
        self.targets: List[CleanTarget] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Temporary Cleaner")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_scan.clicked.connect(self._start_scan)
        header.addWidget(self.btn_scan)

        self.btn_clean = QPushButton("Clean Selected")
        self.btn_clean.setObjectName("DangerButton")
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self._start_clean)
        header.addWidget(self.btn_clean)
        layout.addLayout(header)

        self.status = QLabel("Click Scan to analyze temporary files.")
        layout.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", "Category", "Size", "Files"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        self.lbl_total = QLabel("Total: 0 B")
        layout.addWidget(self.lbl_total)

    def _start_scan(self) -> None:
        self.btn_scan.setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.progress.setVisible(True)
        self.status.setText("Scanning…")
        self.worker = ScanThread()
        self.worker.progress.connect(lambda m: self.status.setText(m))
        self.worker.finished.connect(self._on_scan_done)
        self.worker.start()

    @Slot(list)
    def _on_scan_done(self, targets: List[CleanTarget]) -> None:
        self.targets = targets
        self.progress.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.btn_clean.setEnabled(True)
        self._populate()
        total = sum(t.size_bytes for t in targets)
        self.status.setText(f"Scan complete – {humanize.naturalsize(total)} reclaimable")
        self.main.show_toast("Temp scan finished", "success")

    def _populate(self) -> None:
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.targets))
        total = 0
        for row, t in enumerate(self.targets):
            cb = QCheckBox()
            cb.setChecked(t.selected)
            cb.stateChanged.connect(lambda state, idx=row: self._toggle(idx, state))
            self.table.setCellWidget(row, 0, cb)
            self.table.setItem(row, 1, QTableWidgetItem(t.name))
            self.table.setItem(row, 2, QTableWidgetItem(humanize.naturalsize(t.size_bytes)))
            self.table.setItem(row, 3, QTableWidgetItem(str(t.file_count)))
            total += t.size_bytes
        self.lbl_total.setText(f"Total: {humanize.naturalsize(total)}")

    def _toggle(self, idx: int, state: int) -> None:
        if 0 <= idx < len(self.targets):
            self.targets[idx].selected = state == Qt.Checked

    def _start_clean(self) -> None:
        selected = [t for t in self.targets if t.selected and t.size_bytes > 0]
        if not selected:
            self.main.show_toast("Nothing selected", "warning")
            return
        total = sum(t.size_bytes for t in selected)
        reply = QMessageBox.question(
            self, "Confirm Clean",
            f"Clean {len(selected)} categories ({humanize.naturalsize(total)})?\n\n"
            "Files will be moved to the Recycle Bin where possible.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.btn_clean.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.progress.setVisible(True)
        self.cleaner = CleanThread(self.targets)
        self.cleaner.progress.connect(lambda m: self.status.setText(m))
        self.cleaner.finished.connect(self._on_clean_done)
        self.cleaner.start()

    @Slot(int, int, list)
    def _on_clean_done(self, freed: int, errors: int, msgs: list) -> None:
        self.progress.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.btn_clean.setEnabled(True)
        self.status.setText(
            f"Freed {humanize.naturalsize(freed)}" + (f" ({errors} errors)" if errors else "")
        )
        level = "success" if errors == 0 else "warning"
        self.main.show_toast(f"Freed {humanize.naturalsize(freed)}", level)
        # Re-scan to refresh
        self._start_scan()
