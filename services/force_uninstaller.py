"""Force uninstaller – scans leftovers after official uninstall and offers cleanup."""

from __future__ import annotations

import logging
import os
import shutil
import winreg
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox, QScrollArea, QWidget

from services.programs_scanner import InstalledProgram
from services.restore_point import create_restore_point
from utils.paths import get_backup_dir

logger = logging.getLogger("CleanerPro.ForceUninstall")


class LeftoverItem:
    def __init__(self, path: str, kind: str, size: int = 0):
        self.path = path
        self.kind = kind  # file / folder / registry
        self.size = size
        self.selected = True


class ForceUninstaller:
    def __init__(self, program: InstalledProgram, main_window):
        self.program = program
        self.main = main_window
        self.leftovers: List[LeftoverItem] = []

    def run(self) -> None:
        # 1. Create restore point
        ok = create_restore_point(f"CleanerPro – Force remove {self.program.name}")
        if not ok:
            reply = QMessageBox.warning(
                self.main, "Restore Point",
                "Could not create a System Restore Point. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # 2. Try official uninstall first if available
        if self.program.uninstall_string:
            try:
                import subprocess
                subprocess.run(self.program.uninstall_string, shell=True, timeout=120)
            except Exception as e:
                logger.warning("Official uninstall failed or timed out: %s", e)

        # 3. Scan leftovers
        self.main.show_toast("Scanning for leftovers…", "info")
        self._scan_leftovers()

        if not self.leftovers:
            self.main.show_toast("No leftovers found", "success")
            return

        # 4. Present selection dialog
        selected = self._show_selection_dialog()
        if not selected:
            return

        # 5. Delete selected items
        deleted = 0
        errors = 0
        for item in selected:
            try:
                if item.kind == "registry":
                    self._delete_registry_key(item.path)
                elif item.kind == "folder":
                    shutil.rmtree(item.path, ignore_errors=False)
                else:
                    Path(item.path).unlink(missing_ok=True)
                deleted += 1
            except Exception as e:
                logger.error("Failed to remove %s: %s", item.path, e)
                errors += 1

        self.main.show_toast(
            f"Removed {deleted} items" + (f", {errors} errors" if errors else ""),
            "success" if errors == 0 else "warning"
        )

    def _scan_leftovers(self) -> None:
        name = self.program.name
        # Sanitize common name for folder matching
        safe_name = name.replace(" ", "").lower()
        candidates = [
            name,
            name.split()[0] if " " in name else name,
            self.program.publisher.split()[0] if self.program.publisher else "",
        ]
        candidates = [c for c in candidates if c]

        # Locations to scan
        user_profile = Path(os.environ.get("USERPROFILE", ""))
        locations = [
            (Path(os.environ.get("TEMP", "")), "temp"),
            (Path(os.environ.get("LOCALAPPDATA", "")), "localappdata"),
            (Path(os.environ.get("APPDATA", "")), "appdata"),
            (Path(os.environ.get("PROGRAMDATA", "")), "programdata"),
            (Path(os.environ.get("ProgramFiles", r"C:\Program Files")), "programfiles"),
            (Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")), "programfiles86"),
            (user_profile / "Desktop", "desktop"),
            (Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu", "startmenu"),
        ]

        for base, kind in locations:
            if not base.exists():
                continue
            try:
                for entry in base.iterdir():
                    ename = entry.name.lower()
                    for cand in candidates:
                        if cand.lower() in ename:
                            size = 0
                            if entry.is_file():
                                try:
                                    size = entry.stat().st_size
                                except OSError:
                                    pass
                            self.leftovers.append(LeftoverItem(str(entry), "folder" if entry.is_dir() else "file", size))
                            break
            except PermissionError:
                continue

        # Registry leftovers (HKCU & HKLM Software)
        for hive, root_path in [
            (winreg.HKEY_CURRENT_USER, r"Software"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node"),
        ]:
            try:
                root = winreg.OpenKey(hive, root_path)
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(root, i)
                        i += 1
                        for cand in candidates:
                            if cand.lower() in sub.lower():
                                full = f"{root_path}\\{sub}"
                                self.leftovers.append(LeftoverItem(full, "registry"))
                                break
                    except OSError:
                        break
                winreg.CloseKey(root)
            except OSError:
                pass

        # Also the original uninstall key
        if self.program.registry_key:
            self.leftovers.append(LeftoverItem(self.program.registry_key, "registry"))

        logger.info("Found %d leftover items for %s", len(self.leftovers), name)

    def _show_selection_dialog(self) -> List[LeftoverItem]:
        dlg = QDialog(self.main)
        dlg.setWindowTitle(f"Leftovers – {self.program.name}")
        dlg.resize(600, 450)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel(
            f"Found {len(self.leftovers)} leftover items. Select what to remove:"
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout(container)

        checkboxes = []
        for item in self.leftovers:
            cb = QCheckBox(f"[{item.kind}] {item.path}")
            cb.setChecked(True)
            vbox.addWidget(cb)
            checkboxes.append((cb, item))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.Accepted:
            return []

        return [item for cb, item in checkboxes if cb.isChecked()]

    def _delete_registry_key(self, path: str) -> None:
        # path like SOFTWARE\Vendor\App – try both hives
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                winreg.DeleteKey(hive, path)
                return
            except OSError:
                # May need recursive delete for non-empty keys
                try:
                    self._delete_key_recursive(hive, path)
                    return
                except OSError:
                    continue

    def _delete_key_recursive(self, hive: int, path: str) -> None:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_ALL_ACCESS)
        except OSError:
            return
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
                self._delete_key_recursive(hive, f"{path}\\{sub}")
            except OSError:
                break
        winreg.CloseKey(key)
        winreg.DeleteKey(hive, path)
