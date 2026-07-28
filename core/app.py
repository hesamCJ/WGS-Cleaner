"""Main application window – Cleaner Pro."""

from __future__ import annotations

import logging
from typing import Dict, Type

from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QSizePolicy, QSpacerItem
)

import qtawesome as qta

from core.theme import ThemeManager, ThemeMode
from pages.dashboard import DashboardPage
from pages.programs import ProgramsPage
from pages.disk_analyzer import DiskAnalyzerPage
from pages.duplicates import DuplicatesPage
from pages.temp_cleaner import TempCleanerPage
from pages.browser_cleaner import BrowserCleanerPage
from pages.startup import StartupPage
from pages.processes import ProcessesPage
from pages.services import ServicesPage
from pages.registry import RegistryPage
from pages.one_click import OneClickPage
from pages.health import HealthPage
from pages.system_info import SystemInfoPage
from pages.settings import SettingsPage
from widgets.toast import ToastManager
from services.system_monitor import SystemMonitor

logger = logging.getLogger("CleanerPro.App")


class NavButton(QPushButton):
    """Sidebar navigation button with icon + text."""

    def __init__(self, text: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setIcon(qta.icon(icon_name, color="#A1A1A6"))
        self.setIconSize(QSize(20, 20))
        self.setText(f"  {text}")
        self.setStyleSheet("")  # controlled by global theme


class CleanerProApp(QMainWindow):
    """Primary application shell with sidebar navigation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cleaner Pro")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        self.theme = ThemeManager()
        self.theme.set_mode(ThemeMode.DARK)
        self.setStyleSheet(self.theme.stylesheet())

        self.toast = ToastManager(self)
        self.monitor = SystemMonitor()
        self.monitor.start()

        self._pages: Dict[str, QWidget] = {}
        self._build_ui()
        self._connect_signals()

        # Default page
        self._navigate("dashboard")

        logger.info("Main window initialized")

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(12, 16, 12, 16)
        side_layout.setSpacing(4)

        # Logo / Title
        title = QLabel("Cleaner Pro")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF; padding: 8px 4px 20px 4px;")
        side_layout.addWidget(title)

        # Navigation items
        self.nav_buttons: Dict[str, NavButton] = {}
        nav_items = [
            ("dashboard", "Dashboard", "fa5s.tachometer-alt"),
            ("programs", "Installed Programs", "fa5s.box-open"),
            ("disk", "Disk Analyzer", "fa5s.hdd"),
            ("duplicates", "Duplicate Finder", "fa5s.copy"),
            ("temp", "Temporary Cleaner", "fa5s.broom"),
            ("browser", "Browser Cleaner", "fa5s.globe"),
            ("startup", "Startup Manager", "fa5s.rocket"),
            ("processes", "Process Manager", "fa5s.microchip"),
            ("services", "Windows Services", "fa5s.cogs"),
            ("registry", "Registry Cleaner", "fa5s.database"),
            ("oneclick", "One-Click Optimize", "fa5s.magic"),
            ("health", "SSD / HDD Health", "fa5s.heartbeat"),
            ("sysinfo", "System Information", "fa5s.info-circle"),
            ("settings", "Settings", "fa5s.cog"),
        ]

        for key, label, icon in nav_items:
            btn = NavButton(label, icon)
            btn.clicked.connect(lambda checked, k=key: self._navigate(k))
            self.nav_buttons[key] = btn
            side_layout.addWidget(btn)

        side_layout.addStretch()

        # Version footer
        ver = QLabel("v1.0.0")
        ver.setStyleSheet("color: #636366; font-size: 11px; padding: 8px;")
        side_layout.addWidget(ver)

        root.addWidget(self.sidebar)

        # ── Content area ─────────────────────────────────────────
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # Instantiate pages lazily on first visit for performance
        self._page_classes: Dict[str, Type[QWidget]] = {
            "dashboard": DashboardPage,
            "programs": ProgramsPage,
            "disk": DiskAnalyzerPage,
            "duplicates": DuplicatesPage,
            "temp": TempCleanerPage,
            "browser": BrowserCleanerPage,
            "startup": StartupPage,
            "processes": ProcessesPage,
            "services": ServicesPage,
            "registry": RegistryPage,
            "oneclick": OneClickPage,
            "health": HealthPage,
            "sysinfo": SystemInfoPage,
            "settings": SettingsPage,
        }

    def _navigate(self, key: str) -> None:
        """Switch to a page, creating it if necessary."""
        if key not in self._pages:
            cls = self._page_classes.get(key)
            if cls is None:
                return
            page = cls(self)
            self._pages[key] = page
            self.stack.addWidget(page)
            logger.debug("Created page: %s", key)

        # Update nav button states
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)
            color = "#FFFFFF" if k == key else "#A1A1A6"
            # re-apply icon color
            icon_name = {
                "dashboard": "fa5s.tachometer-alt",
                "programs": "fa5s.box-open",
                "disk": "fa5s.hdd",
                "duplicates": "fa5s.copy",
                "temp": "fa5s.broom",
                "browser": "fa5s.globe",
                "startup": "fa5s.rocket",
                "processes": "fa5s.microchip",
                "services": "fa5s.cogs",
                "registry": "fa5s.database",
                "oneclick": "fa5s.magic",
                "health": "fa5s.heartbeat",
                "sysinfo": "fa5s.info-circle",
                "settings": "fa5s.cog",
            }.get(k, "fa5s.circle")
            btn.setIcon(qta.icon(icon_name, color=color))

        self.stack.setCurrentWidget(self._pages[key])

    def _connect_signals(self) -> None:
        pass

    def show_toast(self, message: str, level: str = "info", duration: int = 3500) -> None:
        self.toast.show(message, level, duration)

    def closeEvent(self, event) -> None:
        self.monitor.stop()
        logger.info("Application closing")
        super().closeEvent(event)
