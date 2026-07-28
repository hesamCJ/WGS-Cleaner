#!/usr/bin/env python3
"""
Build Cleaner Pro into a single-file Windows executable with PyInstaller.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "assets" / "icons" / "app_icon.ico"
MAIN = ROOT / "main.py"
DIST = ROOT / "dist"
NAME = "CleanerPro"


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",           # no console
        "--onefile",            # single EXE
        f"--name={NAME}",
        f"--distpath={DIST}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT / 'build'}",
    ]

    if ICON.exists():
        cmd.append(f"--icon={ICON}")

    # Hidden imports that PyInstaller sometimes misses
    hidden = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "qtawesome",
        "psutil",
        "wmi",
        "win32api",
        "win32con",
        "pythoncom",
        "pywintypes",
        "send2trash",
        "humanize",
        "pyqtgraph",
        "matplotlib",
    ]
    for h in hidden:
        cmd.append(f"--hidden-import={h}")

    # Collect data for qtawesome fonts/icons
    cmd.append("--collect-data=qtawesome")
    cmd.append("--collect-data=pyqtgraph")

    cmd.append(str(MAIN))

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print(f"\nBuild succeeded → {DIST / (NAME + '.exe')}")
    else:
        print("\nBuild failed", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
