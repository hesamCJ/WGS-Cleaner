"""Installed Programs page – icons, per-row actions, search, force remove."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QThread, Signal, QSize, Slot
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QProgressBar, QComboBox, QFrame,
    QSplitter, QFormLayout, QSizePolicy
)

import qtawesome as qta

from core.theme import ThemeManager
from services.programs_scanner import InstalledProgram, scan_installed_programs
from services.force_uninstaller import ForceUninstaller
from utils.icon_loader import load_program_icon
from widgets.program_actions import ProgramActionsWidget

logger = logging.getLogger("CleanerPro.ProgramsPage")


class ScanWorker(QThread):
    finished = Signal(list)
    progress = Signal(str)

    def run(self):
        self.progress.emit("Scanning registry…")
        programs = scan_installed_programs()
        self.finished.emit(programs)


class ProgramsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.theme = ThemeManager()
        self.programs: List[InstalledProgram] = []
        self.filtered: List[InstalledProgram] = []
        self._build_ui()
        self._start_scan()

    # ── UI ──────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("Installed Programs")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(f"color: {self.theme.colors.text_secondary}; font-size: 13px;")
        header.addWidget(self.lbl_count)

        self.btn_refresh = QPushButton(qta.icon("fa5s.sync-alt", color="#FFFFFF"), "  Refresh")
        self.btn_refresh.setObjectName("PrimaryButton")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._start_scan)
        header.addWidget(self.btn_refresh)

        self.btn_export = QPushButton(qta.icon("fa5s.file-export", color="#A1A1A6"), "  Export")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._export_list)
        header.addWidget(self.btn_export)
        layout.addLayout(header)

        # Search + sort
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name, publisher, version…")
        self.search.setMinimumHeight(36)
        self.search.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name A–Z", "Size (largest)", "Install Date", "Publisher"])
        self.sort_combo.setMinimumHeight(36)
        self.sort_combo.setMinimumWidth(150)
        self.sort_combo.currentTextChanged.connect(self._apply_filter)
        filter_row.addWidget(self.sort_combo)
        layout.addLayout(filter_row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Splitter: table + detail panel
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Program", "Version", "Publisher", "Size", "Install Date", "Actions"
        ])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 150)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setIconSize(QSize(28, 28))
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        splitter.addWidget(self.table)

        # Detail panel
        self.detail = QFrame()
        self.detail.setObjectName("Card")
        self.detail.setProperty("class", "Card")
        self.detail.setMinimumWidth(260)
        self.detail.setMaximumWidth(320)
        detail_layout = QVBoxLayout(self.detail)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

        self.detail_icon = QLabel()
        self.detail_icon.setFixedSize(56, 56)
        self.detail_icon.setAlignment(Qt.AlignCenter)
        detail_layout.addWidget(self.detail_icon, alignment=Qt.AlignCenter)

        self.detail_name = QLabel("Select a program")
        self.detail_name.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.detail_name.setWordWrap(True)
        self.detail_name.setAlignment(Qt.AlignCenter)
        detail_layout.addWidget(self.detail_name)

        self.detail_form = QFormLayout()
        self.detail_form.setSpacing(8)
        self.d_version = QLabel("—")
        self.d_publisher = QLabel("—")
        self.d_date = QLabel("—")
        self.d_size = QLabel("—")
        self.d_location = QLabel("—")
        self.d_location.setWordWrap(True)
        self.d_location.setStyleSheet("font-size: 11px;")
        for lbl in (self.d_version, self.d_publisher, self.d_date, self.d_size, self.d_location):
            lbl.setStyleSheet(f"color: {self.theme.colors.text_secondary};")
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.detail_form.addRow("Version:", self.d_version)
        self.detail_form.addRow("Publisher:", self.d_publisher)
        self.detail_form.addRow("Installed:", self.d_date)
        self.detail_form.addRow("Size:", self.d_size)
        self.detail_form.addRow("Location:", self.d_location)
        detail_layout.addLayout(self.detail_form)

        detail_layout.addSpacing(8)

        # Big action buttons in detail panel
        self.btn_d_uninstall = QPushButton(qta.icon("fa5s.trash-alt", color="#FFFFFF"), "  Uninstall")
        self.btn_d_uninstall.setObjectName("PrimaryButton")
        self.btn_d_uninstall.setMinimumHeight(36)
        self.btn_d_uninstall.setCursor(Qt.PointingHandCursor)
        self.btn_d_uninstall.clicked.connect(self._uninstall)
        detail_layout.addWidget(self.btn_d_uninstall)

        self.btn_d_force = QPushButton(qta.icon("fa5s.skull-crossbones", color="#FFFFFF"), "  Force Remove")
        self.btn_d_force.setObjectName("DangerButton")
        self.btn_d_force.setMinimumHeight(36)
        self.btn_d_force.setCursor(Qt.PointingHandCursor)
        self.btn_d_force.clicked.connect(self._force_remove)
        detail_layout.addWidget(self.btn_d_force)

        self.btn_d_folder = QPushButton(qta.icon("fa5s.folder-open", color="#A1A1A6"), "  Open Folder")
        self.btn_d_folder.setCursor(Qt.PointingHandCursor)
        self.btn_d_folder.clicked.connect(self._open_folder)
        detail_layout.addWidget(self.btn_d_folder)

        self.btn_d_reg = QPushButton(qta.icon("fa5s.database", color="#A1A1A6"), "  Registry Key")
        self.btn_d_reg.setCursor(Qt.PointingHandCursor)
        self.btn_d_reg.clicked.connect(self._open_registry)
        detail_layout.addWidget(self.btn_d_reg)

        detail_layout.addStretch()
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        self._set_detail_enabled(False)

    # ── Scan ────────────────────────────────────────────────────────
    def _start_scan(self) -> None:
        self.progress.setVisible(True)
        self.btn_refresh.setEnabled(False)
        self.worker = ScanWorker()
        self.worker.finished.connect(self._on_scan_done)
        self.worker.start()

    @Slot(list)
    def _on_scan_done(self, programs: List[InstalledProgram]) -> None:
        self.programs = programs
        self.progress.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self._apply_filter()
        self.main.show_toast(f"Found {len(programs)} programs", "success")

    # ── Filter / populate ───────────────────────────────────────────
    def _apply_filter(self) -> None:
        query = self.search.text().strip().lower()
        sort_by = self.sort_combo.currentText()

        filtered = self.programs
        if query:
            filtered = [
                p for p in filtered
                if query in p.name.lower()
                or query in p.publisher.lower()
                or query in p.version.lower()
            ]

        if sort_by.startswith("Name"):
            filtered = sorted(filtered, key=lambda p: p.name.lower())
        elif sort_by.startswith("Size"):
            filtered = sorted(filtered, key=lambda p: p.estimated_size_kb, reverse=True)
        elif sort_by.startswith("Install"):
            filtered = sorted(filtered, key=lambda p: p.install_date or "", reverse=True)
        elif sort_by.startswith("Publisher"):
            filtered = sorted(filtered, key=lambda p: p.publisher.lower())

        self.filtered = filtered
        self._populate_table()

    def _populate_table(self) -> None:
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.filtered))

        for row, prog in enumerate(self.filtered):
            # Name + icon
            icon = load_program_icon(prog.icon_path, prog.name, 28)
            name_item = QTableWidgetItem(icon, "  " + prog.name)
            name_item.setData(Qt.UserRole, row)
            self.table.setItem(row, 0, name_item)

            self.table.setItem(row, 1, QTableWidgetItem(prog.version or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(prog.publisher or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(prog.estimated_size_str))
            self.table.setItem(row, 4, QTableWidgetItem(prog.install_date or "—"))

            # Per-row action buttons
            actions = ProgramActionsWidget()
            # Capture prog by default-arg to avoid late-binding
            actions.open_folder.connect(lambda p=prog: self._do_open_folder(p))
            actions.uninstall.connect(lambda p=prog: self._do_uninstall(p))
            actions.force_remove.connect(lambda p=prog: self._do_force_remove(p))
            actions.open_reg.connect(lambda p=prog: self._do_open_registry(p))
            self.table.setCellWidget(row, 5, actions)

        self.lbl_count.setText(f"{len(self.filtered)}  programs")

    # ── Selection / detail ──────────────────────────────────────────
    def _on_selection(self) -> None:
        progs = self._selected_programs()
        if not progs:
            self._set_detail_enabled(False)
            self.detail_name.setText("Select a program")
            self.detail_icon.clear()
            for lbl in (self.d_version, self.d_publisher, self.d_date, self.d_size, self.d_location):
                lbl.setText("—")
            return

        prog = progs[0]
        self._set_detail_enabled(True)
        icon = load_program_icon(prog.icon_path, prog.name, 56)
        self.detail_icon.setPixmap(icon.pixmap(56, 56))
        self.detail_name.setText(prog.name)
        self.d_version.setText(prog.version or "—")
        self.d_publisher.setText(prog.publisher or "—")
        self.d_date.setText(prog.install_date or "—")
        self.d_size.setText(prog.estimated_size_str)
        self.d_location.setText(prog.install_location or "—")

    def _set_detail_enabled(self, enabled: bool) -> None:
        for b in (self.btn_d_uninstall, self.btn_d_force, self.btn_d_folder, self.btn_d_reg):
            b.setEnabled(enabled)

    def _selected_programs(self) -> List[InstalledProgram]:
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        return [self.filtered[r] for r in rows if r < len(self.filtered)]

    # ── Actions (from detail panel / bottom – use selection) ────────
    def _open_folder(self) -> None:
        progs = self._selected_programs()
        if progs:
            self._do_open_folder(progs[0])

    def _uninstall(self) -> None:
        progs = self._selected_programs()
        if progs:
            self._do_uninstall(progs[0])

    def _force_remove(self) -> None:
        progs = self._selected_programs()
        if progs:
            self._do_force_remove(progs[0])

    def _open_registry(self) -> None:
        progs = self._selected_programs()
        if progs:
            self._do_open_registry(progs[0])

    # ── Concrete actions ────────────────────────────────────────────
    def _do_open_folder(self, prog: InstalledProgram) -> None:
        loc = prog.install_location
        if loc and Path(loc).is_dir():
            os.startfile(loc)
        elif prog.icon_path:
            # Fallback: folder of the exe
            clean = prog.icon_path.strip().strip('"').split(",")[0]
            folder = str(Path(clean).parent)
            if Path(folder).is_dir():
                os.startfile(folder)
                return
            self.main.show_toast("Install location not found", "error")
        else:
            self.main.show_toast("Install location not found", "error")

    def _do_open_registry(self, prog: InstalledProgram) -> None:
        key = prog.registry_key
        if not key:
            self.main.show_toast("No registry key", "warning")
            return
        try:
            # Copy key path and open regedit
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(key)
            subprocess.Popen(["regedit"])
            self.main.show_toast(f"Key copied: {key}", "info")
        except Exception as e:
            self.main.show_toast(str(e), "error")

    def _do_uninstall(self, prog: InstalledProgram) -> None:
        if not prog.uninstall_string:
            self.main.show_toast("No uninstall string available — try Force Remove", "warning")
            return
        reply = QMessageBox.question(
            self, "Uninstall",
            f"Uninstall  «{prog.name}» ?\n\nThe official uninstaller will be launched.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            subprocess.Popen(prog.uninstall_string, shell=True)
            self.main.show_toast(f"Uninstaller launched for {prog.name}", "info")
        except Exception as e:
            self.main.show_toast(str(e), "error")

    def _do_force_remove(self, prog: InstalledProgram) -> None:
        reply = QMessageBox.warning(
            self, "Force Remove",
            f"Force remove  «{prog.name}» ?\n\n"
            "• A System Restore Point will be created\n"
            "• Official uninstaller runs first (if available)\n"
            "• Leftovers (registry, AppData, folders…) are scanned\n"
            "• You choose what to delete\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        uninstaller = ForceUninstaller(prog, self.main)
        uninstaller.run()

    # ── Context menu ────────────────────────────────────────────────
    def _context_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu
        progs = self._selected_programs()
        if not progs:
            return
        prog = progs[0]
        menu = QMenu(self)
        menu.addAction(qta.icon("fa5s.folder-open", color="#A1A1A6"), "Open Folder",
                       lambda: self._do_open_folder(prog))
        menu.addAction(qta.icon("fa5s.trash-alt", color="#0A84FF"), "Uninstall",
                       lambda: self._do_uninstall(prog))
        menu.addAction(qta.icon("fa5s.skull-crossbones", color="#FF453A"), "Force Remove",
                       lambda: self._do_force_remove(prog))
        menu.addSeparator()
        menu.addAction(qta.icon("fa5s.database", color="#A1A1A6"), "Open Registry Key",
                       lambda: self._do_open_registry(prog))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # ── Export ──────────────────────────────────────────────────────
    def _export_list(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Program List", "programs.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("Name,Version,Publisher,InstallDate,Size,Location\n")
                for p in self.filtered:
                    f.write(
                        f'"{p.name}","{p.version}","{p.publisher}",'
                        f'"{p.install_date}","{p.estimated_size_str}","{p.install_location}"\n'
                    )
            self.main.show_toast(f"Exported → {path}", "success")
        except Exception as e:
            self.main.show_toast(str(e), "error")
