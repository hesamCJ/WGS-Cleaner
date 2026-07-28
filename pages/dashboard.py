"""Dashboard page – live metrics, charts, system overview."""

from __future__ import annotations

import logging
from datetime import timedelta

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QProgressBar, QSizePolicy
)

from core.theme import ThemeManager
from services.system_monitor import SystemMetrics
from widgets.metric_card import MetricCard
from widgets.chart_widget import UsageChart

logger = logging.getLogger("CleanerPro.Dashboard")


class DashboardPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.theme = ThemeManager()
        self._build_ui()
        # Connect to live monitor
        self.main.monitor.metrics_updated.connect(self._on_metrics)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("Dashboard")
        header.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(header)

        # Metric cards grid
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        self.card_cpu = MetricCard("CPU Usage", "0%", "fa5s.microchip")
        self.card_ram = MetricCard("RAM Usage", "0%", "fa5s.memory")
        self.card_disk = MetricCard("Disk Free", "—", "fa5s.hdd")
        self.card_uptime = MetricCard("Uptime", "—", "fa5s.clock")
        self.card_programs = MetricCard("Installed Programs", "—", "fa5s.box-open")
        self.card_startup = MetricCard("Startup Apps", "—", "fa5s.rocket")

        cards_layout.addWidget(self.card_cpu, 0, 0)
        cards_layout.addWidget(self.card_ram, 0, 1)
        cards_layout.addWidget(self.card_disk, 0, 2)
        cards_layout.addWidget(self.card_uptime, 1, 0)
        cards_layout.addWidget(self.card_programs, 1, 1)
        cards_layout.addWidget(self.card_startup, 1, 2)

        layout.addLayout(cards_layout)

        # Charts row
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        self.cpu_chart = UsageChart("CPU History", self.theme.colors.chart_1)
        self.ram_chart = UsageChart("RAM History", self.theme.colors.chart_2)

        charts_row.addWidget(self.cpu_chart)
        charts_row.addWidget(self.ram_chart)
        layout.addLayout(charts_row)

        # System info strip
        info_frame = QFrame()
        info_frame.setObjectName("Card")
        info_frame.setProperty("class", "Card")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(20, 14, 20, 14)

        self.lbl_os = QLabel("Windows: —")
        self.lbl_os.setStyleSheet(f"color: {self.theme.colors.text_secondary};")
        info_layout.addWidget(self.lbl_os)
        info_layout.addStretch()
        self.lbl_gpu = QLabel("GPU: —")
        self.lbl_gpu.setStyleSheet(f"color: {self.theme.colors.text_secondary};")
        info_layout.addWidget(self.lbl_gpu)

        layout.addWidget(info_frame)
        layout.addStretch()

        # Populate static-ish data once
        self._load_static_counts()

    def _load_static_counts(self) -> None:
        """Load program count and startup count in background-friendly way."""
        try:
            from services.programs_scanner import count_installed_programs
            from services.startup_manager import count_startup_items
            prog_count = count_installed_programs()
            start_count = count_startup_items()
            self.card_programs.set_value(str(prog_count))
            self.card_startup.set_value(str(start_count))
        except Exception as e:
            logger.warning("Static counts failed: %s", e)
            self.card_programs.set_value("N/A")
            self.card_startup.set_value("N/A")

    @Slot(object)
    def _on_metrics(self, m: SystemMetrics) -> None:
        self.card_cpu.set_value(f"{m.cpu_percent:.0f}%")
        self.card_ram.set_value(f"{m.ram_percent:.0f}%")
        self.card_disk.set_value(f"{m.disk_free_gb:.1f} GB free")
        self.card_uptime.set_value(self._format_uptime(m.uptime_seconds))

        self.cpu_chart.add_point(m.cpu_percent)
        self.ram_chart.add_point(m.ram_percent)

        self.lbl_os.setText(f"OS: {m.windows_version}")
        if m.gpu_percent is not None:
            self.lbl_gpu.setText(f"GPU: {m.gpu_percent:.0f}%")
        else:
            self.lbl_gpu.setText("GPU: N/A")

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        td = timedelta(seconds=int(seconds))
        days = td.days
        hours, rem = divmod(td.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        if days:
            return f"{days}d {hours}h {minutes}m"
        return f"{hours}h {minutes}m"
