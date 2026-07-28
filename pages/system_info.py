"""System Information page."""

from __future__ import annotations

import platform
import socket
import uuid
from datetime import datetime

import psutil
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFormLayout, QGroupBox
)

from core.theme import ThemeManager


class SystemInfoPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("System Information")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        btn = QPushButton("Refresh")
        btn.setObjectName("PrimaryButton")
        btn.clicked.connect(self._load)
        header.addWidget(btn)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.form_layout = QVBoxLayout(self.container)
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def _load(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # OS
        self._add_group("Operating System", [
            ("System", platform.system()),
            ("Release", platform.release()),
            ("Version", platform.version()),
            ("Architecture", platform.machine()),
            ("Hostname", socket.gethostname()),
            ("Username", psutil.users()[0].name if psutil.users() else "—"),
        ])

        # CPU
        freq = psutil.cpu_freq()
        self._add_group("Processor", [
            ("CPU", platform.processor() or "—"),
            ("Physical cores", str(psutil.cpu_count(logical=False))),
            ("Logical cores", str(psutil.cpu_count(logical=True))),
            ("Max frequency", f"{freq.max:.0f} MHz" if freq else "—"),
            ("Current frequency", f"{freq.current:.0f} MHz" if freq else "—"),
        ])

        # Memory
        mem = psutil.virtual_memory()
        self._add_group("Memory", [
            ("Total", f"{mem.total / (1024**3):.2f} GB"),
            ("Available", f"{mem.available / (1024**3):.2f} GB"),
            ("Used", f"{mem.used / (1024**3):.2f} GB ({mem.percent}%)"),
        ])

        # Disks
        disk_rows = []
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
                disk_rows.append((
                    f"{p.device} ({p.mountpoint})",
                    f"{u.total / (1024**3):.1f} GB total, {u.free / (1024**3):.1f} GB free"
                ))
            except Exception:
                continue
        self._add_group("Drives", disk_rows)

        # Network
        net_rows = []
        for name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if a.family.name == "AF_INET":
                    net_rows.append((name, a.address))
        self._add_group("Network", net_rows or [("—", "No interfaces")])

        # Boot
        boot = datetime.fromtimestamp(psutil.boot_time())
        self._add_group("Boot", [
            ("Boot time", boot.strftime("%Y-%m-%d %H:%M:%S")),
            ("Machine GUID", str(uuid.getnode())),
        ])

        self.main.show_toast("System info refreshed", "info")

    def _add_group(self, title: str, rows: list):
        group = QGroupBox(title)
        form = QFormLayout(group)
        for label, value in rows:
            form.addRow(QLabel(label + ":"), QLabel(str(value)))
        self.form_layout.addWidget(group)
