"""One-Click Optimize – runs multiple cleaners and reports results."""

from __future__ import annotations

import time
from typing import List

import humanize
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QCheckBox, QGroupBox, QMessageBox
)

from services.temp_cleaner import get_clean_targets, scan_targets, clean_targets
from services.restore_point import create_restore_point


class OptimizeWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)

    def __init__(self, options: dict):
        super().__init__()
        self.options = options

    def run(self):
        start = time.time()
        freed = 0
        errors = 0
        log: List[str] = []

        if self.options.get("restore_point"):
            self.progress.emit("Creating restore point…")
            ok = create_restore_point("CleanerPro One-Click Optimize")
            log.append("Restore point: " + ("OK" if ok else "FAILED"))

        if self.options.get("temp"):
            self.progress.emit("Scanning temporary files…")
            targets = get_clean_targets()
            for t in targets:
                t.selected = True
            scan_targets(targets, lambda m: self.progress.emit(m))
            self.progress.emit("Cleaning temporary files…")
            f, e, msgs = clean_targets(targets, progress_cb=lambda m: self.progress.emit(m))
            freed += f
            errors += e
            log.append(f"Temp cleanup: {humanize.naturalsize(f)}")
            log.extend(msgs[:5])

        if self.options.get("dns"):
            self.progress.emit("Flushing DNS…")
            import subprocess
            try:
                subprocess.run(
                    ["ipconfig", "/flushdns"], capture_output=True, timeout=15,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                log.append("DNS cache flushed")
            except Exception as ex:
                log.append(f"DNS flush error: {ex}")
                errors += 1

        elapsed = time.time() - start
        self.finished.emit({
            "freed": freed,
            "errors": errors,
            "elapsed": elapsed,
            "log": log,
        })


class OneClickPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("One-Click Optimize")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(title)

        desc = QLabel(
            "Run a comprehensive cleanup in one click. "
            "A System Restore Point is created before any changes."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        group = QGroupBox("Options")
        g_layout = QVBoxLayout(group)
        self.cb_temp = QCheckBox("Temporary files & caches")
        self.cb_temp.setChecked(True)
        g_layout.addWidget(self.cb_temp)
        self.cb_dns = QCheckBox("Flush DNS cache")
        self.cb_dns.setChecked(True)
        g_layout.addWidget(self.cb_dns)
        self.cb_restore = QCheckBox("Create System Restore Point")
        self.cb_restore.setChecked(True)
        g_layout.addWidget(self.cb_restore)
        layout.addWidget(group)

        self.btn_run = QPushButton("Optimize Now")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_run.setMinimumHeight(48)
        self.btn_run.clicked.connect(self._run)
        layout.addWidget(self.btn_run)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status = QLabel("")
        layout.addWidget(self.status)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)
        layout.addWidget(self.log)
        layout.addStretch()

    def _run(self):
        if QMessageBox.question(
            self, "Confirm",
            "Start One-Click Optimize?\nThis will clean selected categories."
        ) != QMessageBox.Yes:
            return
        self.btn_run.setEnabled(False)
        self.progress.setVisible(True)
        self.log.clear()
        opts = {
            "temp": self.cb_temp.isChecked(),
            "dns": self.cb_dns.isChecked(),
            "restore_point": self.cb_restore.isChecked(),
        }
        self.worker = OptimizeWorker(opts)
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(dict)
    def _on_done(self, result: dict):
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.status.setText(
            f"Done – Freed {humanize.naturalsize(result['freed'])} in {result['elapsed']:.1f}s"
        )
        self.log.append("\n".join(result["log"]))
        level = "success" if result["errors"] == 0 else "warning"
        self.main.show_toast(
            f"Optimized – {humanize.naturalsize(result['freed'])} freed", level
        )
