"""Extract and cache Windows application icons."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication

import qtawesome as qta

logger = logging.getLogger("CleanerPro.IconLoader")

_cache: dict[str, QIcon] = {}


def _fallback_icon(name: str = "") -> QIcon:
    """Generate a letter-avatar style fallback icon."""
    letter = (name[:1] or "A").upper()
    pix = QPixmap(48, 48)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    # Colored circle based on letter
    colors = [
        "#0A84FF", "#30D158", "#FF9F0A", "#BF5AF2",
        "#FF453A", "#64D2FF", "#FFD60A", "#AC8E68",
    ]
    color = QColor(colors[ord(letter) % len(colors)])
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 2, 44, 44)
    p.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", 18, QFont.Bold)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignCenter, letter)
    p.end()
    return QIcon(pix)


def load_program_icon(icon_path: str, name: str = "", size: int = 32) -> QIcon:
    """
    Load icon from a Windows DisplayIcon path.
    Handles forms like:
      C:\\Path\\app.exe
      C:\\Path\\app.exe,0
      C:\\Path\\icon.ico
    """
    if not icon_path:
        return _fallback_icon(name)

    cache_key = f"{icon_path}|{size}"
    if cache_key in _cache:
        return _cache[cache_key]

    # Strip ,index suffix
    clean = icon_path.strip().strip('"')
    if "," in clean:
        clean = clean.rsplit(",", 1)[0].strip().strip('"')

    path = Path(clean)
    icon = QIcon()

    if path.exists() and path.is_file():
        suffix = path.suffix.lower()
        try:
            if suffix in (".ico", ".png", ".bmp", ".jpg", ".jpeg", ".gif"):
                icon = QIcon(str(path))
            elif suffix in (".exe", ".dll"):
                # QIcon can extract from PE resources on Windows
                icon = QIcon(str(path))
                if icon.isNull():
                    # Try win32gui ExtractIcon if available
                    icon = _extract_win32_icon(str(path), size)
        except Exception as e:
            logger.debug("Icon load failed for %s: %s", path, e)

    if icon.isNull() or icon.availableSizes() == []:
        icon = _fallback_icon(name)

    _cache[cache_key] = icon
    return icon


def _extract_win32_icon(path: str, size: int = 32) -> QIcon:
    """Extract icon from exe/dll via pywin32 (Windows only)."""
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        from PySide6.QtGui import QImage

        large, small = win32gui.ExtractIconEx(path, 0)
        if not large and not small:
            return QIcon()
        hicon = large[0] if large else small[0]
        try:
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, size, size)
            hdc_mem = hdc.CreateCompatibleDC()
            hdc_mem.SelectObject(hbmp)
            hdc_mem.DrawIcon((0, 0), hicon)
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            img = QImage(bmpstr, bmpinfo["bmWidth"], bmpinfo["bmHeight"], QImage.Format_ARGB32)
            pix = QPixmap.fromImage(img.rgbSwapped())
            return QIcon(pix)
        finally:
            for h in (large or []) + (small or []):
                try:
                    win32gui.DestroyIcon(h)
                except Exception:
                    pass
    except Exception as e:
        logger.debug("win32 icon extract failed: %s", e)
    return QIcon()
