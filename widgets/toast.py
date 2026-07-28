"""Modern animated toast notifications."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup
)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QGraphicsOpacityEffect

from core.theme import ThemeManager


class Toast(QLabel):
    def __init__(self, message: str, level: str, parent: QWidget):
        super().__init__(message, parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        theme = ThemeManager()
        colors = {
            "info": theme.colors.info,
            "success": theme.colors.success,
            "warning": theme.colors.warning,
            "error": theme.colors.error,
        }
        bg = colors.get(level, theme.colors.info)

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: #FFFFFF;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 500;
            }}
        """)
        self.setFont(QFont("Segoe UI", 10))
        self.adjustSize()

        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.opacity.setOpacity(0.0)

    def fade_in(self):
        anim = QPropertyAnimation(self.opacity, b"opacity")
        anim.setDuration(250)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim  # keep reference

    def fade_out(self, finished_cb=None):
        anim = QPropertyAnimation(self.opacity, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        if finished_cb:
            anim.finished.connect(finished_cb)
        anim.start()
        self._anim = anim


class ToastManager:
    def __init__(self, parent: QWidget):
        self.parent = parent
        self._active: List[Toast] = []

    def show(self, message: str, level: str = "info", duration: int = 3500) -> None:
        toast = Toast(message, level, self.parent)
        toast.adjustSize()

        # Position bottom-right
        margin = 24
        x = self.parent.width() - toast.width() - margin
        y = self.parent.height() - toast.height() - margin - len(self._active) * (toast.height() + 8)
        toast.move(x, y)
        toast.show()
        toast.fade_in()
        self._active.append(toast)

        QTimer.singleShot(duration, lambda: self._dismiss(toast))

    def _dismiss(self, toast: Toast) -> None:
        if toast not in self._active:
            return

        def cleanup():
            toast.hide()
            toast.deleteLater()
            if toast in self._active:
                self._active.remove(toast)

        toast.fade_out(cleanup)
