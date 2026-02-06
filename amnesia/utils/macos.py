"""macOS filesystem helper utilities."""

from __future__ import annotations

from pathlib import Path


def expand_user_path(path: str) -> Path:
    return Path(path).expanduser()


def default_imessage_db_path() -> Path:
    return expand_user_path("~/Library/Messages/chat.db")
