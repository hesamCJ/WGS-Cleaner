"""Settings page – theme, language, paths, startup, etc."""

from __future__ import annotations

import os
import sys
import winreg
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QGroupBox, QFormLayout, QLineEdit, QFileDialog, QMessageBox
)

from core.theme import ThemeManager, ThemeMode
from utils.paths import get_backup_dir, BACKUP


class SettingsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.theme = ThemeManager()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(title)

        # Appearance
        appearance = QGroupBox("Appearance")
        form = QFormLayout(appearance)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.theme_combo.setCurrentText(
            "Dark" if self.theme.mode == ThemeMode.DARK else
            "Light" if self.theme.mode == ThemeMode.LIGHT else "System"
        )
        self.theme_combo.currentTextChanged.connect(self._on_theme)
        form.addRow("Theme:", self.theme_combo)
        layout.addWidget(appearance)

        # Behavior
        behavior = QGroupBox("Behavior")
        b_layout = QVBoxLayout(behavior)
        self.cb_startup = QCheckBox("Start Cleaner Pro with Windows")
        self.cb_startup.setChecked(self._is_startup_enabled())
        self.cb_startup.stateChanged.connect(self._toggle_startup)
        b_layout.addWidget(self.cb_startup)
        self.cb_notifications = QCheckBox("Show toast notifications")
        self.cb_notifications.setChecked(True)
        b_layout.addWidget(self.cb_notifications)
        layout.addWidget(behavior)

        # Paths
        paths = QGroupBox("Paths")
        p_form = QFormLayout(paths)
        self.backup_edit = QLineEdit(str(get_backup_dir()))
        self.backup_edit.setReadOnly(True)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_backup)
        row = QHBoxLayout()
        row.addWidget(self.backup_edit)
        row.addWidget(btn_browse)
        p_form.addRow("Backup folder:", row)
        layout.addWidget(paths)

        # About
        about = QGroupBox("About")
        a_layout = QVBoxLayout(about)
        a_layout.addWidget(QLabel("Cleaner Pro v1.0.0"))
        a_layout.addWidget(QLabel("Production-ready Windows optimization suite."))
        a_layout.addWidget(QLabel("Built with Python 3.13 + PySide6"))
        layout.addWidget(about)

        layout.addStretch()

    def _on_theme(self, text: str):
        mode = {
            "Dark": ThemeMode.DARK,
            "Light": ThemeMode.LIGHT,
            "System": ThemeMode.SYSTEM,
        }.get(text, ThemeMode.DARK)
        self.theme.set_mode(mode)
        self.main.setStyleSheet(self.theme.stylesheet())
        self.main.show_toast(f"Theme set to {text}", "info")

    def _is_startup_enabled(self) -> bool:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            winreg.QueryValueEx(key, "CleanerPro")
            winreg.CloseKey(key)
            return True
        except OSError:
            return False

    def _toggle_startup(self, state: int):
        run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE)
            if state == Qt.Checked:
                exe = sys.executable
                # Prefer the frozen exe if running as such
                if getattr(sys, "frozen", False):
                    exe = sys.executable
                else:
                    exe = f'"{sys.executable}" "{Path(__file__).resolve().parent.parent / "main.py"}"'
                winreg.SetValueEx(key, "CleanerPro", 0, winreg.REG_SZ, exe)
                self.main.show_toast("Added to Windows startup", "success")
            else:
                try:
                    winreg.DeleteValue(key, "CleanerPro")
                except OSError:
                    pass
                self.main.show_toast("Removed from Windows startup", "info")
            winreg.CloseKey(key)
        except OSError as e:
            self.main.show_toast(f"Startup change failed: {e}", "error")

    def _browse_backup(self):
        path = QFileDialog.getExistingDirectory(self, "Select backup folder", str(get_backup_dir()))
        if path:
            self.backup_edit.setText(path)
            # In a full app we would persist this to a config file
            self.main.show_toast(f"Backup folder set to {path}", "info")
