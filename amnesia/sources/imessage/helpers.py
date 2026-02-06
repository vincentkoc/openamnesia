"""Helper utilities for iMessage source."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from amnesia.utils.macos import default_imessage_db_path

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)


def resolve_imessage_db_path(configured_path: str | None = None) -> Path:
    if configured_path:
        return Path(configured_path).expanduser()
    return default_imessage_db_path()


def parse_apple_message_date(raw_value: int | float | None) -> datetime | None:
    if raw_value is None:
        return None

    value = float(raw_value)
    if value <= 0:
        return None

    # macOS Messages may store date as either seconds or nanoseconds since 2001-01-01.
    if value > 10_000_000_000:
        seconds = value / 1_000_000_000.0
    else:
        seconds = value

    return APPLE_EPOCH + timedelta(seconds=seconds)
