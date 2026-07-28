"""Startup programs manager – registry + Startup folder."""

from __future__ import annotations

import logging
import os
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger("CleanerPro.Startup")

STARTUP_REG = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
]


@dataclass
class StartupItem:
    name: str
    command: str
    location: str  # registry path or folder
    enabled: bool = True
    hive: int = 0
    key_path: str = ""
    impact: str = "Unknown"


def _read_run_key(hive: int, path: str) -> List[StartupItem]:
    items = []
    try:
        key = winreg.OpenKey(hive, path)
    except OSError:
        return items
    i = 0
    while True:
        try:
            name, value, _ = winreg.EnumValue(key, i)
            i += 1
            items.append(StartupItem(
                name=name,
                command=str(value),
                location=path,
                enabled=True,
                hive=hive,
                key_path=path,
            ))
        except OSError:
            break
    winreg.CloseKey(key)
    return items


def scan_startup_items() -> List[StartupItem]:
    items: List[StartupItem] = []
    for hive, path in STARTUP_REG:
        items.extend(_read_run_key(hive, path))

    # Startup folders
    folders = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
    ]
    for folder in folders:
        if not folder.exists():
            continue
        for entry in folder.iterdir():
            if entry.suffix.lower() in (".lnk", ".exe", ".bat", ".cmd"):
                items.append(StartupItem(
                    name=entry.stem,
                    command=str(entry),
                    location=str(folder),
                    enabled=True,
                ))
    return items


def count_startup_items() -> int:
    return len(scan_startup_items())


def disable_startup_item(item: StartupItem) -> bool:
    """Disable by deleting the Run value (or renaming for folders)."""
    if item.key_path:
        try:
            key = winreg.OpenKey(item.hive, item.key_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, item.name)
            winreg.CloseKey(key)
            return True
        except OSError as e:
            logger.error("Disable failed: %s", e)
            return False
    # Folder item – rename to .disabled
    p = Path(item.command)
    if p.exists():
        try:
            p.rename(p.with_suffix(p.suffix + ".disabled"))
            return True
        except OSError:
            return False
    return False


def enable_startup_item(item: StartupItem, command: str) -> bool:
    if item.key_path:
        try:
            key = winreg.OpenKey(item.hive, item.key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, item.name, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            return True
        except OSError:
            return False
    return False


def delete_startup_item(item: StartupItem) -> bool:
    return disable_startup_item(item)
