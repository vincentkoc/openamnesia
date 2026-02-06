"""Reporting helpers for iMessage source operations."""

from __future__ import annotations

from amnesia.sources.imessage.types import IMessageReadOutput


def summarize_read(output: IMessageReadOutput) -> dict:
    return {
        "messages": len(output.messages),
        "max_rowid_seen": output.max_rowid_seen,
        "db_path": output.meta.get("db_path"),
    }
