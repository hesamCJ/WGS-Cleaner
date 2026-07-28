"""Per-row action buttons for the Programs table."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QSizePolicy

import qtawesome as qta


class ProgramActionsWidget(QWidget):
    """Compact icon-only action bar for a single program row."""

    open_folder = Signal()
    uninstall = Signal()
    force_remove = Signal()
    open_reg = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        def make_btn(icon_name: str, tip: str, color: str, danger: bool = False) -> QToolButton:
            btn = QToolButton()
            btn.setIcon(qta.icon(icon_name, color=color))
            btn.setIconSize(QSize(16, 16))
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAutoRaise(True)
            btn.setFixedSize(30, 28)
            if danger:
                btn.setStyleSheet("""
                    QToolButton {
                        border: none; border-radius: 6px; background: transparent;
                    }
                    QToolButton:hover {
                        background: rgba(255, 69, 58, 0.25);
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QToolButton {
                        border: none; border-radius: 6px; background: transparent;
                    }
                    QToolButton:hover {
                        background: rgba(10, 132, 255, 0.25);
                    }
                """)
            return btn

        self.btn_folder = make_btn("fa5s.folder-open", "Open install folder", "#A1A1A6")
        self.btn_uninstall = make_btn("fa5s.trash-alt", "Uninstall", "#0A84FF")
        self.btn_force = make_btn("fa5s.skull-crossbones", "Force Remove (leftovers)", "#FF453A", danger=True)
        self.btn_reg = make_btn("fa5s.database", "Open registry key", "#A1A1A6")

        self.btn_folder.clicked.connect(self.open_folder.emit)
        self.btn_uninstall.clicked.connect(self.uninstall.emit)
        self.btn_force.clicked.connect(self.force_remove.emit)
        self.btn_reg.clicked.connect(self.open_reg.emit)

        layout.addWidget(self.btn_folder)
        layout.addWidget(self.btn_uninstall)
        layout.addWidget(self.btn_force)
        layout.addWidget(self.btn_reg)
        layout.addStretch()
