from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC

from amnesia.connectors.base import SourceRecord
from amnesia.models import Event, utc_now


def normalize_records(records: list[SourceRecord]) -> list[Event]:
    events: list[Event] = []
    turn_counters: dict[str, int] = defaultdict(int)

    for record in records:
        ts = record.ts or utc_now()
        ts = ts.astimezone(UTC)
        raw_session = record.session_hint or stable_session_id(
            f"{record.source}:{record.file_path}"
        )
        session_id = f"{record.source}:{raw_session}"
        turn_index = turn_counters[session_id]
        turn_counters[session_id] += 1

        event_id = stable_event_id(
            record.source,
            file_path=record.file_path,
            line_number=record.line_number,
            content=record.content,
        )

        events.append(
            Event(
                event_id=event_id,
                ts=ts,
                source=record.source,
                session_id=session_id,
                turn_index=turn_index,
                actor=record.actor,
                content=record.content,
                tool_name=record.tool_name,
                tool_status=record.tool_status,
                tool_args_json=record.tool_args_json,
                tool_result_json=record.tool_result_json,
                meta_json=record.metadata,
            )
        )

    return events


def stable_event_id(source: str, file_path: str, line_number: int, content: str) -> str:
    seed = f"{source}|{file_path}|{line_number}|{content}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def stable_session_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
