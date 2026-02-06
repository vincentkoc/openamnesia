"""macOS filesystem helper utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path


def expand_user_path(path: str) -> Path:
    return Path(path).expanduser()


def default_imessage_db_path() -> Path:
    return expand_user_path("~/Library/Messages/chat.db")


def open_full_disk_access_settings() -> bool:
    url = "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
    try:
        subprocess.run(["open", url], check=False, capture_output=True)
        return True
    except Exception:
        return False
