from __future__ import annotations

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def get_youcom_api_key() -> str | None:
    value = os.environ.get("YOUCOM_API_KEY", "").strip()
    return value or None


def get_composio_api_key() -> str | None:
    value = os.environ.get("COMPOSIO_API_KEY", "").strip()
    return value or None


def vendor_status() -> dict[str, bool]:
    return {
        "youcom": bool(get_youcom_api_key()),
        "composio": bool(get_composio_api_key()),
    }
