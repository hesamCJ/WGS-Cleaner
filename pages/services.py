"""Windows Services manager."""

from __future__ import annotations

import logging
from typing import List

import psutil
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QLineEdit
)

logger = logging.getLogger("CleanerPro.Services")


class ServicesWorker(QThread):
    finished = Signal(list)

    def run(self):
        result = []
        try:
            # Prefer WMI if available for richer info
            import wmi
            c = wmi.WMI()
            for s in c.Win32_Service():
                result.append({
                    "name": s.Name,
                    "display": s.DisplayName or s.Name,
                    "status": s.State,
                    "start_mode": s.StartMode,
                    "pid": s.ProcessId or 0,
                })
        except Exception:
            # Fallback: limited via psutil
            for p in psutil.win_service_iter():
                try:
                    info = p.as_dict()
                    result.append({
                        "name": info.get("name", ""),
                        "display": info.get("display_name", ""),
                        "status": info.get("status", ""),
                        "start_mode": info.get("start_type", ""),
                        "pid": info.get("pid") or 0,
                    })
                except Exception:
                    continue
        self.finished.emit(result)


class ServicesPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.services: List[dict] = []
        self._build_ui()
        self._scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Windows Services")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter services…")
        self.search.textChanged.connect(self._populate)
        header.addWidget(self.search)
        btn = QPushButton("Refresh")
        btn.setObjectName("PrimaryButton")
        btn.clicked.connect(self._scan)
        header.addWidget(btn)
        layout.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Display Name", "Status", "Start Mode", "PID"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        bar = QHBoxLayout()
        for label, slot in [
            ("Start", self._start), ("Stop", self._stop),
            ("Restart", self._restart), ("Set Automatic", lambda: self._set_mode("Automatic")),
            ("Set Manual", lambda: self._set_mode("Manual")), ("Disable", lambda: self._set_mode("Disabled")),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch()
        layout.addLayout(bar)

    def _scan(self):
        self.worker = ServicesWorker()
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(list)
    def _on_done(self, services: list):
        self.services = services
        self._populate()
        self.main.show_toast(f"{len(services)} services", "info")

    def _populate(self):
        query = self.search.text().strip().lower()
        filtered = [
            s for s in self.services
            if not query or query in s["name"].lower() or query in (s["display"] or "").lower()
        ]
        self.table.setRowCount(len(filtered))
        for i, s in enumerate(filtered):
            self.table.setItem(i, 0, QTableWidgetItem(s["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(s["display"]))
            self.table.setItem(i, 2, QTableWidgetItem(s["status"]))
            self.table.setItem(i, 3, QTableWidgetItem(s["start_mode"]))
            self.table.setItem(i, 4, QTableWidgetItem(str(s["pid"])))
        self._filtered = filtered

    def _selected_name(self) -> str | None:
        rows = set(i.row() for i in self.table.selectedIndexes())
        if not rows or not hasattr(self, "_filtered"):
            return None
        return self._filtered[min(rows)]["name"]

    def _control(self, action: str):
        name = self._selected_name()
        if not name:
            self.main.show_toast("Select a service", "warning")
            return
        try:
            import wmi
            c = wmi.WMI()
            svc = c.Win32_Service(Name=name)[0]
            if action == "start":
                svc.StartService()
            elif action == "stop":
                svc.StopService()
            elif action == "restart":
                svc.StopService()
                svc.StartService()
            self.main.show_toast(f"{action.title()} {name}", "success")
            self._scan()
        except Exception as e:
            self.main.show_toast(str(e), "error")

    def _start(self):
        self._control("start")

    def _stop(self):
        self._control("stop")

    def _restart(self):
        self._control("restart")

    def _set_mode(self, mode: str):
        name = self._selected_name()
        if not name:
            return
        try:
            import wmi
            c = wmi.WMI()
            svc = c.Win32_Service(Name=name)[0]
            svc.ChangeStartMode(mode)
            self.main.show_toast(f"Set {name} to {mode}", "success")
            self._scan()
        except Exception as e:
            self.main.show_toast(str(e), "error")
