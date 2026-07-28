"""Live usage chart using pyqtgraph for smooth 60 FPS-ish updates."""

from __future__ import annotations

from collections import deque
from typing import Deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

import pyqtgraph as pg

from core.theme import ThemeManager


class UsageChart(QFrame):
    MAX_POINTS = 60

    def __init__(self, title: str, line_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("class", "Card")
        self.setMinimumHeight(220)

        theme = ThemeManager()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {theme.colors.text_secondary}; font-size: 12px; font-weight: 600;")
        layout.addWidget(lbl)

        # Configure pyqtgraph for dark/light
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget()
        self.plot.setBackground(None)
        self.plot.showGrid(x=False, y=True, alpha=0.15)
        self.plot.setYRange(0, 100)
        self.plot.setXRange(0, self.MAX_POINTS)
        self.plot.hideAxis("bottom")
        self.plot.getAxis("left").setTextPen(QColor(theme.colors.text_secondary))
        self.plot.getAxis("left").setPen(QColor(theme.colors.border))
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setMenuEnabled(False)

        self.data: Deque[float] = deque([0.0] * self.MAX_POINTS, maxlen=self.MAX_POINTS)
        pen = pg.mkPen(color=line_color, width=2)
        self.curve = self.plot.plot(list(self.data), pen=pen, fillLevel=0,
                                    brush=pg.mkBrush(QColor(line_color + "40")))

        layout.addWidget(self.plot)

    def add_point(self, value: float) -> None:
        self.data.append(max(0.0, min(100.0, value)))
        self.curve.setData(list(self.data))
