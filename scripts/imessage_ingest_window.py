#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

from amnesia.sdk.imessage import IMessageIngestConfig, run_imessage_ingest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest iMessage for a small time window.")
    parser.add_argument("--days", type=int, default=2, help="Number of days back from now.")
    parser.add_argument("--limit", type=int, default=500, help="Max messages to read.")
    parser.add_argument("--db-path", default="~/Library/Messages/chat.db")
    parser.add_argument("--store-dsn", default="sqlite:///./data/amnesia.db")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    since = (datetime.now(UTC) - timedelta(days=max(1, args.days))).isoformat(timespec="seconds")

    cfg = IMessageIngestConfig(
        db_path=args.db_path,
        store_dsn=args.store_dsn,
        limit=args.limit,
        reset_state=True,
        save_state=False,
        since=since,
    )
    result = run_imessage_ingest(cfg)
    print(
        "imessage ingest",
        f"seen={result.seen}",
        f"ingested={result.ingested}",
        f"events={result.events}",
        f"sessions={result.sessions}",
        f"moments={result.moments}",
        f"filtered={result.filtered}",
        f"error={result.error}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
