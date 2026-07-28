"""Create Windows System Restore Points before dangerous operations."""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

logger = logging.getLogger("CleanerPro.RestorePoint")


def create_restore_point(description: str = "Cleaner Pro Restore Point") -> bool:
    """
    Create a system restore point using PowerShell.
    Requires administrator privileges for reliability.
    Returns True on success.
    """
    # Escape description for PowerShell
    safe_desc = description.replace('"', "'")
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        f'Checkpoint-Computer -Description "{safe_desc}" -RestorePointType MODIFY_SETTINGS'
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        if result.returncode == 0:
            logger.info("Restore point created: %s", description)
            return True
        logger.warning("Restore point failed: %s %s", result.stdout, result.stderr)
        return False
    except Exception as e:
        logger.exception("Restore point error: %s", e)
        return False
