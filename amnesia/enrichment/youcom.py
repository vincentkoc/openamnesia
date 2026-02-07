from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


def youcom_search(query: str, *, count: int = 3, freshness: str = "month") -> list[dict[str, Any]]:
    api_key = os.environ.get("YOUCOM_API_KEY", "").strip()
    if not api_key or not query:
        return []
    base = "https://ydc-index.io/v1/search"
    params = {
        "query": query,
        "count": str(max(1, min(10, count))),
        "freshness": freshness,
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-API-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    return _extract_results(payload)


def _extract_results(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    results = []
    web = payload.get("web") or {}
    items = web.get("results") if isinstance(web, dict) else None
    if not isinstance(items, list):
        items = payload.get("results") if isinstance(payload.get("results"), list) else []
    for item in list(items)[:10]:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": item.get("title") or item.get("name"),
                "url": item.get("url") or item.get("link"),
                "snippet": item.get("snippet") or item.get("description"),
            }
        )
    return results
