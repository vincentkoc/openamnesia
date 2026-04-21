#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from amnesia.sources.imessage.imessage import read_messages
from amnesia.sources.imessage.types import IMessageReadInput


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe iMessage DB for a small time window.")
    parser.add_argument("--days", type=int, default=2, help="Number of days back from now.")
    parser.add_argument("--limit", type=int, default=50, help="Max messages to read.")
    parser.add_argument("--db-path", default="~/Library/Messages/chat.db")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    since = (datetime.now(UTC) - timedelta(days=max(1, args.days))).isoformat(timespec="seconds")

    output = read_messages(
        IMessageReadInput(
            source="imessage",
            state={},
            options={"since_ts": since, "limit": args.limit},
            db_path=str(Path(args.db_path).expanduser()),
            min_rowid_exclusive=0,
            limit=args.limit,
        )
    )

    print(f"db_missing={output.meta.get('missing')}")
    print(f"messages={len(output.messages)} since={since}")
    for msg in output.messages[:10]:
        ts = msg.ts.isoformat() if msg.ts else "none"
        text = (msg.text or "").replace("\\n", " ").strip()
        print(f"- {ts} {msg.chat_id} {msg.sender}: {text[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
