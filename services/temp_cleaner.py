"""Temporary files and system cache cleaner."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Callable, Optional

from send2trash import send2trash

logger = logging.getLogger("CleanerPro.TempCleaner")


@dataclass
class CleanTarget:
    name: str
    paths: List[Path]
    description: str = ""
    selected: bool = True
    size_bytes: int = 0
    file_count: int = 0


def _safe_size(path: Path) -> tuple[int, int]:
    """Return (total_bytes, file_count) for a path, ignoring errors."""
    total = 0
    count = 0
    if not path.exists():
        return 0, 0
    try:
        if path.is_file():
            return path.stat().st_size, 1
        for root, dirs, files in os.walk(path, topdown=True):
            # Skip junctions / reparse points that can cause loops
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for f in files:
                try:
                    fp = Path(root) / f
                    total += fp.stat().st_size
                    count += 1
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass
    return total, count


def get_clean_targets() -> List[CleanTarget]:
    """Build the list of known temporary / cache locations."""
    user = Path(os.environ.get("USERPROFILE", ""))
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    temp = Path(os.environ.get("TEMP", ""))

    targets = [
        CleanTarget("Windows Temp", [windir / "Temp"], "System temporary files"),
        CleanTarget("User Temp", [temp], "Current user temporary files"),
        CleanTarget("Prefetch", [windir / "Prefetch"], "Application prefetch data"),
        CleanTarget(
            "Windows Update Cache",
            [windir / "SoftwareDistribution" / "Download"],
            "Downloaded Windows Update files",
        ),
        CleanTarget(
            "Thumbnail Cache",
            [local / "Microsoft" / "Windows" / "Explorer"],
            "Thumbnail database (thumbcache_*.db)",
        ),
        CleanTarget(
            "Delivery Optimization",
            [windir / "ServiceProfiles" / "NetworkService" / "AppData" / "Local" / "Microsoft" / "Windows" / "DeliveryOptimization" / "Cache"],
            "Delivery Optimization cache",
        ),
        CleanTarget(
            "Crash Dumps",
            [local / "CrashDumps", windir / "Minidump"],
            "Application and system crash dumps",
        ),
        CleanTarget(
            "Memory Dumps",
            [windir / "MEMORY.DMP"],
            "Full memory dump (if present)",
        ),
        CleanTarget(
            "Error Reports",
            [local / "Microsoft" / "Windows" / "WER", windir / "System32" / "config" / "systemprofile" / "AppData" / "Local" / "Microsoft" / "Windows" / "WER"],
            "Windows Error Reporting files",
        ),
        CleanTarget(
            "Recent Files",
            [user / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Recent"],
            "Recent documents shortcuts",
        ),
        CleanTarget(
            "Font Cache",
            [local / "FontCache", windir / "ServiceProfiles" / "LocalService" / "AppData" / "Local" / "FontCache"],
            "Font cache files",
        ),
        CleanTarget(
            "DirectX Shader Cache",
            [local / "D3DSCache"],
            "DirectX shader cache",
        ),
        CleanTarget(
            "Logs",
            [windir / "Logs", local / "Temp"],
            "Various log files",
        ),
    ]
    return targets


def scan_targets(targets: List[CleanTarget], progress_cb: Optional[Callable[[str], None]] = None) -> List[CleanTarget]:
    """Calculate sizes for each target."""
    for t in targets:
        if progress_cb:
            progress_cb(f"Scanning {t.name}…")
        total = 0
        count = 0
        for p in t.paths:
            s, c = _safe_size(p)
            total += s
            count += c
        t.size_bytes = total
        t.file_count = count
    return targets


def clean_targets(
    targets: List[CleanTarget],
    use_recycle_bin: bool = True,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> tuple[int, int, List[str]]:
    """
    Clean selected targets.
    Returns (freed_bytes, error_count, error_messages).
    """
    freed = 0
    errors = 0
    messages: List[str] = []

    for t in targets:
        if not t.selected or t.size_bytes == 0:
            continue
        if progress_cb:
            progress_cb(f"Cleaning {t.name}…")
        for path in t.paths:
            if not path.exists():
                continue
            try:
                if path.is_file():
                    size = path.stat().st_size
                    if use_recycle_bin:
                        send2trash(str(path))
                    else:
                        path.unlink()
                    freed += size
                else:
                    # Clean contents of directory, keep the dir itself
                    for entry in path.iterdir():
                        try:
                            if entry.is_file() or entry.is_symlink():
                                size = entry.stat().st_size if entry.is_file() else 0
                                if use_recycle_bin:
                                    send2trash(str(entry))
                                else:
                                    entry.unlink()
                                freed += size
                            elif entry.is_dir():
                                size = _safe_size(entry)[0]
                                if use_recycle_bin:
                                    send2trash(str(entry))
                                else:
                                    shutil.rmtree(entry, ignore_errors=True)
                                freed += size
                        except Exception as e:
                            errors += 1
                            messages.append(f"{entry}: {e}")
            except Exception as e:
                errors += 1
                messages.append(f"{path}: {e}")

    # Extra: empty Recycle Bin
    try:
        if progress_cb:
            progress_cb("Emptying Recycle Bin…")
        subprocess.run(
            ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
            capture_output=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception:
        pass

    # DNS cache flush
    try:
        if progress_cb:
            progress_cb("Flushing DNS cache…")
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception:
        pass

    return freed, errors, messages
