"""Scan installed programs from Windows Registry and filesystem."""

from __future__ import annotations

import logging
import os
import winreg
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Iterator

import humanize

logger = logging.getLogger("CleanerPro.Programs")

# Registry locations that list uninstallable software
UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]


@dataclass
class InstalledProgram:
    name: str
    version: str = ""
    publisher: str = ""
    install_date: str = ""
    install_location: str = ""
    uninstall_string: str = ""
    quiet_uninstall: str = ""
    estimated_size_kb: int = 0
    actual_size_bytes: int = 0
    icon_path: str = ""
    registry_key: str = ""
    hive: int = 0

    @property
    def estimated_size_str(self) -> str:
        if self.estimated_size_kb > 0:
            return humanize.naturalsize(self.estimated_size_kb * 1024, binary=True)
        if self.actual_size_bytes > 0:
            return humanize.naturalsize(self.actual_size_bytes, binary=True)
        return "—"

    @property
    def actual_size_str(self) -> str:
        if self.actual_size_bytes > 0:
            return humanize.naturalsize(self.actual_size_bytes, binary=True)
        return "—"


def _read_reg_str(key, name: str, default: str = "") -> str:
    try:
        val, _ = winreg.QueryValueEx(key, name)
        return str(val) if val else default
    except OSError:
        return default


def _read_reg_int(key, name: str, default: int = 0) -> int:
    try:
        val, _ = winreg.QueryValueEx(key, name)
        return int(val)
    except (OSError, ValueError, TypeError):
        return default


def _enumerate_uninstall_key(hive: int, path: str) -> Iterator[InstalledProgram]:
    try:
        root = winreg.OpenKey(hive, path)
    except OSError:
        return

    i = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(root, i)
            i += 1
        except OSError:
            break

        try:
            sub = winreg.OpenKey(root, subkey_name)
        except OSError:
            continue

        try:
            name = _read_reg_str(sub, "DisplayName")
            if not name:
                continue
            # Skip system components / updates that lack DisplayName or are flagged
            system_component = _read_reg_int(sub, "SystemComponent", 0)
            if system_component == 1:
                continue
            parent = _read_reg_str(sub, "ParentKeyName")
            if parent:
                continue

            version = _read_reg_str(sub, "DisplayVersion")
            publisher = _read_reg_str(sub, "Publisher")
            location = _read_reg_str(sub, "InstallLocation")
            uninstall = _read_reg_str(sub, "UninstallString")
            quiet = _read_reg_str(sub, "QuietUninstallString")
            size_kb = _read_reg_int(sub, "EstimatedSize", 0)
            icon = _read_reg_str(sub, "DisplayIcon")
            date_raw = _read_reg_str(sub, "InstallDate")  # YYYYMMDD

            install_date = ""
            if date_raw and len(date_raw) == 8 and date_raw.isdigit():
                try:
                    install_date = datetime.strptime(date_raw, "%Y%m%d").strftime("%Y-%m-%d")
                except ValueError:
                    install_date = date_raw

            # Clean icon path (often "path,0")
            if icon and "," in icon:
                icon = icon.split(",")[0].strip('"')

            yield InstalledProgram(
                name=name,
                version=version,
                publisher=publisher,
                install_date=install_date,
                install_location=location.strip('"') if location else "",
                uninstall_string=uninstall,
                quiet_uninstall=quiet,
                estimated_size_kb=size_kb,
                icon_path=icon.strip('"') if icon else "",
                registry_key=f"{path}\\{subkey_name}",
                hive=hive,
            )
        finally:
            winreg.CloseKey(sub)

    winreg.CloseKey(root)


def scan_installed_programs() -> List[InstalledProgram]:
    """Return a de-duplicated list of installed programs."""
    seen = set()
    results: List[InstalledProgram] = []

    for hive, path in UNINSTALL_KEYS:
        for prog in _enumerate_uninstall_key(hive, path):
            key = (prog.name.lower(), prog.version)
            if key in seen:
                continue
            seen.add(key)
            results.append(prog)

    results.sort(key=lambda p: p.name.lower())
    logger.info("Found %d installed programs", len(results))
    return results


def count_installed_programs() -> int:
    return len(scan_installed_programs())


def calculate_folder_size(path: str) -> int:
    """Recursively calculate folder size in bytes. Returns 0 on error."""
    total = 0
    p = Path(path)
    if not p.is_dir():
        return 0
    try:
        for entry in p.rglob("*"):
            try:
                if entry.is_file():
                    total += entry.stat().st_size
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return total
