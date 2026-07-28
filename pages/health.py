"""SSD / HDD Health using SMART data."""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QGridLayout,
    QAbstractItemView
)

from core.theme import ThemeManager
from widgets.metric_card import MetricCard

logger = logging.getLogger("CleanerPro.Health")


class HealthWorker(QThread):
    finished = Signal(list)

    def run(self):
        drives = []
        # Try pySMART
        try:
            from pySMART import DeviceList
            for dev in DeviceList():
                drives.append({
                    "name": str(dev.name),
                    "model": getattr(dev, "model", "Unknown"),
                    "serial": getattr(dev, "serial", "—"),
                    "firmware": getattr(dev, "firmware", "—"),
                    "interface": getattr(dev, "interface", "—"),
                    "capacity": str(getattr(dev, "capacity", "—")),
                    "temperature": getattr(dev, "temperature", None),
                    "assessment": str(getattr(dev, "assessment", "—")),
                    "power_on_hours": None,
                    "health_pct": None,
                })
                # Try to extract attributes
                try:
                    for attr in dev.attributes:
                        if attr and attr.name:
                            if "Power_On_Hours" in attr.name or "Power-On Hours" in attr.name:
                                drives[-1]["power_on_hours"] = attr.raw
                            if "Temperature" in attr.name and drives[-1]["temperature"] is None:
                                drives[-1]["temperature"] = attr.raw
                except Exception:
                    pass
        except Exception as e:
            logger.warning("pySMART unavailable: %s", e)
            # Fallback via WMI
            try:
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    drives.append({
                        "name": disk.DeviceID or disk.Caption,
                        "model": disk.Model or "Unknown",
                        "serial": (disk.SerialNumber or "—").strip(),
                        "firmware": disk.FirmwareRevision or "—",
                        "interface": disk.InterfaceType or "—",
                        "capacity": f"{int(disk.Size or 0) / (1024**3):.1f} GB" if disk.Size else "—",
                        "temperature": None,
                        "assessment": "Unknown (SMART requires admin / pySMART)",
                        "power_on_hours": None,
                        "health_pct": None,
                    })
            except Exception as e2:
                logger.warning("WMI disk fallback failed: %s", e2)
        self.finished.emit(drives)


class HealthPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build_ui()
        self._scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("SSD / HDD Health")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        btn = QPushButton("Refresh")
        btn.setObjectName("PrimaryButton")
        btn.clicked.connect(self._scan)
        header.addWidget(btn)
        layout.addLayout(header)

        self.cards_layout = QHBoxLayout()
        layout.addLayout(self.cards_layout)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Device", "Model", "Serial", "Firmware", "Capacity", "Temp", "Assessment"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        note = QLabel(
            "Note: Full SMART data (temperature, life remaining, power-on hours) "
            "requires administrator privileges and a compatible drive. "
            "Install smartmontools or run as admin for best results."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #A1A1A6; font-size: 11px;")
        layout.addWidget(note)

    def _scan(self):
        self.worker = HealthWorker()
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    @Slot(list)
    def _on_done(self, drives: list):
        self.table.setRowCount(len(drives))
        # Clear cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, d in enumerate(drives):
            self.table.setItem(i, 0, QTableWidgetItem(str(d.get("name", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(d.get("model", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(str(d.get("serial", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(str(d.get("firmware", ""))))
            self.table.setItem(i, 4, QTableWidgetItem(str(d.get("capacity", ""))))
            temp = d.get("temperature")
            self.table.setItem(i, 5, QTableWidgetItem(f"{temp}°C" if temp is not None else "—"))
            self.table.setItem(i, 6, QTableWidgetItem(str(d.get("assessment", "—"))))

            card = MetricCard(
                d.get("model", "Drive")[:24],
                str(d.get("assessment", "—")),
                "fa5s.hdd"
            )
            self.cards_layout.addWidget(card)

        self.main.show_toast(f"{len(drives)} drives found", "info")

