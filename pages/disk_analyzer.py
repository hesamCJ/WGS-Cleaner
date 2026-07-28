"""Disk Analyzer – largest folders/files, charts, delete support."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

import humanize
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressBar, QMessageBox, QSplitter
)

from core.theme import ThemeManager


class DiskScanWorker(QThread):
    finished = Signal(list)  # list of (path, size)
    progress = Signal(str)

    def __init__(self, root: str, max_depth: int = 3):
        super().__init__()
        self.root = root
        self.max_depth = max_depth

    def run(self):
        results: List[Tuple[str, int]] = []
        root = Path(self.root)
        self.progress.emit(f"Scanning {self.root}…")
        try:
            for entry in root.iterdir():
                if entry.is_dir():
                    size = self._dir_size(entry, 0)
                    results.append((str(entry), size))
                elif entry.is_file():
                    try:
                        results.append((str(entry), entry.stat().st_size))
                    except OSError:
                        pass
        except PermissionError:
            pass
        results.sort(key=lambda x: x[1], reverse=True)
        self.finished.emit(results[:200])

    def _dir_size(self, path: Path, depth: int) -> int:
        total = 0
        if depth > self.max_depth:
            return 0
        try:
            for entry in path.iterdir():
                try:
                    if entry.is_file():
                        total += entry.stat().st_size
                    elif entry.is_dir() and not entry.is_symlink():
                        total += self._dir_size(entry, depth + 1)
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
        return total


class DiskAnalyzerPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Disk Analyzer")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        self.drive_combo = QComboBox()
        for p in psutil_disk_partitions():
            self.drive_combo.addItem(f"{p.device} ({p.mountpoint})", p.mountpoint)
        header.addWidget(self.drive_combo)

        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_scan.clicked.connect(self._scan)
        header.addWidget(self.btn_scan)
        layout.addLayout(header)

        self.status = QLabel("Select a drive and click Scan.")
        layout.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Path", "Size"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tree, 1)

        bar = QHBoxLayout()
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)
        bar.addStretch()
        layout.addLayout(bar)

    def _scan(self):
        root = self.drive_combo.currentData()
        if not root:
            return
        self.progress.setVisible(True)
        self.btn_scan.setEnabled(False)
        self.worker = DiskScanWorker(root)
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(list)
    def _on_done(self, results: list):
        self.progress.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.tree.clear()
        for path, size in results:
            item = QTreeWidgetItem([path, humanize.naturalsize(size)])
            item.setData(0, Qt.UserRole, path)
            self.tree.addTopLevelItem(item)
        self.status.setText(f"Found {len(results)} largest items")
        self.main.show_toast("Disk scan complete", "success")

    def _delete(self):
        items = self.tree.selectedItems()
        if not items:
            self.main.show_toast("Select items first", "warning")
            return
        paths = [it.data(0, Qt.UserRole) for it in items]
        if QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(paths)} item(s)?\nThis cannot be easily undone."
        ) != QMessageBox.Yes:
            return
        from send2trash import send2trash
        ok = 0
        for p in paths:
            try:
                send2trash(p)
                ok += 1
            except Exception as e:
                logger_msg = str(e)
        self.main.show_toast(f"Deleted {ok} items", "success")
        self._scan()


def psutil_disk_partitions():
    import psutil
    return psutil.disk_partitions(all=False)
