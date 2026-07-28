"""Reusable metric card widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel

import qtawesome as qta

from core.theme import ThemeManager


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "—", icon_name: str = "fa5s.circle", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("class", "Card")
        self.setMinimumHeight(110)
        self.setMinimumWidth(180)

        theme = ThemeManager()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Top: icon + title
        top = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=theme.colors.accent).pixmap(22, 22))
        top.addWidget(icon)
        top.addSpacing(8)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {theme.colors.text_secondary}; font-size: 12px;")
        top.addWidget(lbl_title)
        top.addStretch()
        layout.addLayout(top)

        # Value
        self.lbl_value = QLabel(value)
        self.lbl_value.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.lbl_value.setStyleSheet(f"color: {theme.colors.text_primary};")
        layout.addWidget(self.lbl_value)
        layout.addStretch()

    def set_value(self, value: str) -> None:
        self.lbl_value.setText(value)
