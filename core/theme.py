"""Theme management – Dark / Light with Fluent Design aesthetics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeMode(Enum):
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


@dataclass(frozen=True)
class ThemeColors:
    # Backgrounds
    background: str
    surface: str
    surface_variant: str
    card: str
    sidebar: str
    # Text
    text_primary: str
    text_secondary: str
    text_disabled: str
    # Accent
    accent: str
    accent_hover: str
    accent_pressed: str
    # Status
    success: str
    warning: str
    error: str
    info: str
    # Borders & dividers
    border: str
    divider: str
    # Charts
    chart_1: str
    chart_2: str
    chart_3: str
    chart_4: str


DARK = ThemeColors(
    background="#1C1C1E",
    surface="#2C2C2E",
    surface_variant="#3A3A3C",
    card="#2C2C2E",
    sidebar="#1A1A1C",
    text_primary="#FFFFFF",
    text_secondary="#A1A1A6",
    text_disabled="#636366",
    accent="#0A84FF",
    accent_hover="#409CFF",
    accent_pressed="#0066CC",
    success="#30D158",
    warning="#FFD60A",
    error="#FF453A",
    info="#64D2FF",
    border="#38383A",
    divider="#3A3A3C",
    chart_1="#0A84FF",
    chart_2="#30D158",
    chart_3="#FF9F0A",
    chart_4="#BF5AF2",
)

LIGHT = ThemeColors(
    background="#F2F2F7",
    surface="#FFFFFF",
    surface_variant="#F2F2F7",
    card="#FFFFFF",
    sidebar="#FFFFFF",
    text_primary="#000000",
    text_secondary="#6C6C70",
    text_disabled="#AEAEB2",
    accent="#007AFF",
    accent_hover="#0066D6",
    accent_pressed="#0055B3",
    success="#34C759",
    warning="#FF9500",
    error="#FF3B30",
    info="#5AC8FA",
    border="#C6C6C8",
    divider="#E5E5EA",
    chart_1="#007AFF",
    chart_2="#34C759",
    chart_3="#FF9500",
    chart_4="#AF52DE",
)


class ThemeManager:
    """Singleton-style theme manager."""

    _instance: "ThemeManager | None" = None

    def __new__(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._mode = ThemeMode.DARK
            cls._instance._colors = DARK
        return cls._instance

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def colors(self) -> ThemeColors:
        return self._colors

    def set_mode(self, mode: ThemeMode) -> None:
        self._mode = mode
        if mode == ThemeMode.SYSTEM:
            try:
                import darkdetect
                self._colors = DARK if darkdetect.isDark() else LIGHT
            except Exception:
                self._colors = DARK
        else:
            self._colors = DARK if mode == ThemeMode.DARK else LIGHT
        self._apply_palette()

    def _apply_palette(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        palette = QPalette()
        c = self._colors
        palette.setColor(QPalette.Window, QColor(c.background))
        palette.setColor(QPalette.WindowText, QColor(c.text_primary))
        palette.setColor(QPalette.Base, QColor(c.surface))
        palette.setColor(QPalette.AlternateBase, QColor(c.surface_variant))
        palette.setColor(QPalette.Text, QColor(c.text_primary))
        palette.setColor(QPalette.Button, QColor(c.surface))
        palette.setColor(QPalette.ButtonText, QColor(c.text_primary))
        palette.setColor(QPalette.Highlight, QColor(c.accent))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        palette.setColor(QPalette.ToolTipBase, QColor(c.surface))
        palette.setColor(QPalette.ToolTipText, QColor(c.text_primary))
        palette.setColor(QPalette.Link, QColor(c.accent))
        palette.setColor(QPalette.PlaceholderText, QColor(c.text_disabled))
        app.setPalette(palette)

    def stylesheet(self) -> str:
        """Return a comprehensive Fluent-inspired stylesheet."""
        c = self._colors
        return f"""
        /* Global */
        QWidget {{
            background-color: {c.background};
            color: {c.text_primary};
            font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
            font-size: 13px;
        }}

        /* Sidebar */
        #Sidebar {{
            background-color: {c.sidebar};
            border-right: 1px solid {c.border};
        }}
        #Sidebar QPushButton {{
            background-color: transparent;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            text-align: left;
            color: {c.text_secondary};
            font-size: 13px;
            font-weight: 500;
        }}
        #Sidebar QPushButton:hover {{
            background-color: {c.surface_variant};
            color: {c.text_primary};
        }}
        #Sidebar QPushButton:checked {{
            background-color: {c.accent};
            color: #FFFFFF;
        }}

        /* Cards */
        .Card, QFrame.Card {{
            background-color: {c.card};
            border: 1px solid {c.border};
            border-radius: 12px;
        }}

        /* Buttons */
        QPushButton {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
            padding: 8px 16px;
            color: {c.text_primary};
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c.surface_variant};
            border-color: {c.accent};
        }}
        QPushButton:pressed {{
            background-color: {c.accent_pressed};
            color: #FFFFFF;
        }}
        QPushButton#PrimaryButton {{
            background-color: {c.accent};
            border: none;
            color: #FFFFFF;
        }}
        QPushButton#PrimaryButton:hover {{
            background-color: {c.accent_hover};
        }}
        QPushButton#DangerButton {{
            background-color: {c.error};
            border: none;
            color: #FFFFFF;
        }}
        QPushButton#DangerButton:hover {{
            background-color: #FF6961;
        }}

        /* Line edits / Search */
        QLineEdit {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
            padding: 8px 12px;
            selection-background-color: {c.accent};
        }}
        QLineEdit:focus {{
            border-color: {c.accent};
        }}

        /* Tables */
        QTableWidget, QTreeWidget, QListWidget {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
            gridline-color: {c.divider};
            outline: none;
        }}
        QTableWidget::item, QTreeWidget::item, QListWidget::item {{
            padding: 6px;
            border: none;
        }}
        QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
            background-color: {c.accent};
            color: #FFFFFF;
        }}
        QHeaderView::section {{
            background-color: {c.surface_variant};
            color: {c.text_secondary};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {c.border};
            font-weight: 600;
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c.border};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c.text_disabled};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        /* Progress bars */
        QProgressBar {{
            background-color: {c.surface_variant};
            border: none;
            border-radius: 6px;
            text-align: center;
            color: {c.text_primary};
            height: 12px;
        }}
        QProgressBar::chunk {{
            background-color: {c.accent};
            border-radius: 6px;
        }}

        /* Tabs */
        QTabWidget::pane {{
            border: 1px solid {c.border};
            border-radius: 8px;
            background: {c.surface};
        }}
        QTabBar::tab {{
            background: transparent;
            color: {c.text_secondary};
            padding: 8px 16px;
            margin-right: 4px;
            border-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background: {c.accent};
            color: #FFFFFF;
        }}
        QTabBar::tab:hover:!selected {{
            background: {c.surface_variant};
        }}

        /* ComboBox */
        QComboBox {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            border-radius: 8px;
            padding: 6px 12px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.surface};
            border: 1px solid {c.border};
            selection-background-color: {c.accent};
        }}

        /* Tooltips */
        QToolTip {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 6px;
            padding: 6px;
        }}

        /* GroupBox */
        QGroupBox {{
            border: 1px solid {c.border};
            border-radius: 10px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }}
        """
