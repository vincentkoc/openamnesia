"""Shared logging helpers for the ingestion service."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from amnesia.constants import DEFAULT_LOG_LEVEL, ENV_LOG_LEVEL

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False
_configured_level: int | None = None


def _coerce_level(level: int | str | None) -> int:
    if isinstance(level, int):
        return level
    normalized = str(level or "").strip().upper()
    if not normalized:
        normalized = _resolve_log_level(DEFAULT_LOG_LEVEL)
    value = getattr(logging, normalized, None)
    if isinstance(value, int):
        return value
    if normalized.isdigit():
        return int(normalized)
    raise ValueError(f"Unknown log level: {level}")


def setup_logging(level: int | str | None = None, *, force: bool = False) -> None:
    global _configured
    global _configured_level

    target_level = _coerce_level(level)
    if _configured and not force and _configured_level == target_level:
        return

    logging.basicConfig(
        level=target_level,
        format=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        force=True,
    )

    # Keep noisy libs quiet by default.
    for name in ("urllib3", "requests", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)

    _configured = True
    _configured_level = target_level


def _resolve_log_level(default: str = DEFAULT_LOG_LEVEL) -> str:
    raw = os.getenv(ENV_LOG_LEVEL, "").strip().upper()
    return raw or default


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def debug_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    payload = {"event": event, **fields}
    logger.debug(json.dumps(payload, ensure_ascii=True, sort_keys=True))
