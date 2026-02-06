"""Shared logging helpers for the ingestion service."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from rich.logging import RichHandler

from amnesia.constants import DEFAULT_LOG_LEVEL, ENV_LOG_LEVEL

DEFAULT_LOG_FORMAT = "%(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_DEBUG_CLIP = 220

_configured = False
_configured_level: int | None = None


def resolve_log_level(default: str = DEFAULT_LOG_LEVEL) -> str:
    """Resolve effective log level from environment with a sane fallback."""
    raw = os.getenv(ENV_LOG_LEVEL, "").strip().upper()
    return raw or default


def _coerce_level(level: int | str | None) -> int:
    if isinstance(level, int):
        return level
    normalized = str(level or "").strip().upper()
    if not normalized:
        normalized = resolve_log_level(DEFAULT_LOG_LEVEL)
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

    handler = RichHandler(
        level=target_level,
        markup=True,
        rich_tracebacks=False,
        show_time=True,
        show_level=True,
        show_path=False,
    )
    base_level = target_level if target_level >= logging.WARNING else logging.WARNING
    logging.basicConfig(
        level=base_level,
        format=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        handlers=[handler],
        force=True,
    )
    logging.getLogger().setLevel(target_level)
    logging.getLogger("amnesia").setLevel(target_level)

    # Keep noisy libs quiet by default.
    for name in (
        "urllib3",
        "requests",
        "httpx",
        "httpcore",
        "LiteLLM",
        "litellm",
        "openai",
        "matplotlib",
        "matplotlib.font_manager",
        "fontTools",
        "asyncio",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in ("LiteLLM", "litellm", "matplotlib", "matplotlib.font_manager", "fontTools"):
        logging.getLogger(name).setLevel(logging.ERROR)

    _configured = True
    _configured_level = target_level


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _format_debug_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=True, sort_keys=True)
        except Exception:
            return f"dict({len(value)})"
    if isinstance(value, (list, tuple, set)):
        return f"{type(value).__name__}({len(value)})"
    return str(value)


def _clip_debug_text(text: str, limit: int = DEFAULT_DEBUG_CLIP) -> str:
    compact = " ".join(text.split())
    if limit > 0 and len(compact) > limit:
        return compact[:limit] + "..."
    return compact


def debug_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_debug_value(value)}")
    logger.debug(_clip_debug_text(" ".join(parts)))
