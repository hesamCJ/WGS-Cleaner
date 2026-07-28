"""Duplicate file finder using SHA-256."""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import humanize
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressBar, QFileDialog, QMessageBox
)

from core.theme import ThemeManager


class DupWorker(QThread):
    finished = Signal(dict)  # hash -> list of paths
    progress = Signal(str)

    def __init__(self, roots: List[str], extensions: List[str] | None):
        super().__init__()
        self.roots = roots
        self.extensions = extensions  # None = all

    def run(self):
        size_map: Dict[int, List[Path]] = defaultdict(list)
        # First pass: group by size
        for root in self.roots:
            self.progress.emit(f"Indexing {root}…")
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    p = Path(dirpath) / fn
                    if self.extensions and p.suffix.lower() not in self.extensions:
                        continue
                    try:
                        size = p.stat().st_size
                        if size > 0:
                            size_map[size].append(p)
                    except OSError:
                        continue

        # Second pass: hash groups with size > 1
        hash_map: Dict[str, List[str]] = defaultdict(list)
        candidates = {s: paths for s, paths in size_map.items() if len(paths) > 1}
        total = sum(len(v) for v in candidates.values())
        done = 0
        for size, paths in candidates.items():
            for p in paths:
                done += 1
                if done % 20 == 0:
                    self.progress.emit(f"Hashing… {done}/{total}")
                try:
                    h = self._sha256(p)
                    hash_map[h].append(str(p))
                except OSError:
                    continue

        # Keep only real duplicates
        dups = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
        self.finished.emit(dups)

    @staticmethod
    def _sha256(path: Path, chunk: int = 65536) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()


class DuplicatesPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.dups: dict = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Duplicate Finder")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        self.scope = QComboBox()
        self.scope.addItems(["Everything", "Pictures", "Videos", "Documents"])
        header.addWidget(self.scope)

        self.btn_scan = QPushButton("Scan Folder…")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_scan.clicked.connect(self._choose_and_scan)
        header.addWidget(self.btn_scan)
        layout.addLayout(header)

        self.status = QLabel("Choose a folder to scan for duplicates.")
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File / Hash", "Size"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.tree, 1)

        bar = QHBoxLayout()
        self.btn_delete = QPushButton("Delete Selected Duplicates")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(self._delete)
        bar.addWidget(self.btn_delete)
        bar.addStretch()
        layout.addLayout(bar)

    def _choose_and_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder to scan")
        if not folder:
            return
        ext_map = {
            "Pictures": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"],
            "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"],
            "Everything": None,
        }
        exts = ext_map.get(self.scope.currentText())
        self.progress.setVisible(True)
        self.btn_scan.setEnabled(False)
        self.worker = DupWorker([folder], exts)
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(dict)
    def _on_done(self, dups: dict):
        self.progress.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.dups = dups
        self.tree.clear()
        for h, paths in dups.items():
            parent = QTreeWidgetItem([f"Hash {h[:12]}… ({len(paths)} files)", ""])
            for p in paths:
                try:
                    size = humanize.naturalsize(Path(p).stat().st_size)
                except OSError:
                    size = "?"
                child = QTreeWidgetItem([p, size])
                child.setData(0, Qt.UserRole, p)
                parent.addChild(child)
            self.tree.addTopLevelItem(parent)
        self.status.setText(f"Found {len(dups)} duplicate groups")
        self.main.show_toast(f"{len(dups)} duplicate groups", "success")

    def _delete(self):
        items = self.tree.selectedItems()
        paths = []
        for it in items:
            p = it.data(0, Qt.UserRole)
            if p:
                paths.append(p)
        if not paths:
            self.main.show_toast("Select specific files (not groups)", "warning")
            return
        if QMessageBox.question(self, "Delete", f"Delete {len(paths)} files?") != QMessageBox.Yes:
            return
        from send2trash import send2trash
        ok = 0
        for p in paths:
            try:
                send2trash(p)
                ok += 1
            except Exception:
                pass
        self.main.show_toast(f"Deleted {ok} files", "success")
