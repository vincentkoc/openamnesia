from __future__ import annotations

from datetime import datetime, timezone

from amnesia.connectors.base import SourceRecord
from amnesia.pipeline.normalize import normalize_records
from amnesia.pipeline.sessionize import sessionize_events


def test_normalize_prefixes_source_in_session_id() -> None:
    records = [
        SourceRecord(
            source="cursor",
            file_path="a.jsonl",
            line_number=1,
            content="hello",
            ts=datetime(2026, 2, 6, 0, 0, tzinfo=timezone.utc),
            session_hint="abc",
        )
    ]

    events = normalize_records(records)
    assert events[0].session_id == "cursor:abc"


def test_sessionize_uses_session_key() -> None:
    records = [
        SourceRecord(
            source="terminal",
            file_path="x.log",
            line_number=1,
            content="run",
            ts=datetime(2026, 2, 6, 0, 0, tzinfo=timezone.utc),
            session_hint="s1",
        )
    ]
    sessions = sessionize_events(normalize_records(records))
    assert sessions[0].session_key == "terminal:s1"
