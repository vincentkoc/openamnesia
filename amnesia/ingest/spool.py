"""Local spool queue for decoupling file IO from processing."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from amnesia.connectors.base import SourceRecord


@dataclass(slots=True)
class SpoolSegment:
    path: Path
    record_count: int


class JsonlSpool:
    def __init__(self, root: Path, *, max_records_per_segment: int = 10_000) -> None:
        self.root = root
        self.max_records_per_segment = max_records_per_segment
        self.root.mkdir(parents=True, exist_ok=True)

    def write_records(self, records: Iterable[SourceRecord]) -> list[SpoolSegment]:
        segments: list[SpoolSegment] = []
        current_records = 0
        current_path: Path | None = None
        fh = None

        def _open_new_segment() -> tuple[Path, object]:
            seg_name = f"segment_{uuid.uuid4().hex}.jsonl"
            seg_path = self.root / seg_name
            return seg_path, seg_path.open("w", encoding="utf-8")

        try:
            for record in records:
                if fh is None or current_records >= self.max_records_per_segment:
                    if fh is not None and current_path is not None:
                        fh.close()
                        segments.append(
                            SpoolSegment(path=current_path, record_count=current_records)
                        )
                    current_path, fh = _open_new_segment()
                    current_records = 0

                payload = {
                    "source": record.source,
                    "file_path": record.file_path,
                    "line_number": record.line_number,
                    "content": record.content,
                    "ts": record.ts.isoformat() if record.ts is not None else None,
                    "session_hint": record.session_hint,
                    "group_hint": record.group_hint,
                    "actor": record.actor,
                    "tool_name": record.tool_name,
                    "tool_status": record.tool_status,
                    "tool_args_json": record.tool_args_json,
                    "tool_result_json": record.tool_result_json,
                    "metadata": record.metadata,
                }
                fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
                current_records += 1

            if fh is not None and current_path is not None:
                fh.close()
                segments.append(SpoolSegment(path=current_path, record_count=current_records))
        finally:
            if fh is not None and not fh.closed:
                fh.close()

        return segments

    def iter_records(self, segments: list[SpoolSegment]) -> Iterator[SourceRecord]:
        for segment in segments:
            with segment.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    row = json.loads(line)
                    yield SourceRecord(
                        source=str(row.get("source", "")),
                        file_path=str(row.get("file_path", "")),
                        line_number=int(row.get("line_number", 0)),
                        content=str(row.get("content", "")),
                        ts=_parse_ts(row.get("ts")),
                        session_hint=row.get("session_hint"),
                        group_hint=row.get("group_hint"),
                        actor=str(row.get("actor", "user")),
                        tool_name=row.get("tool_name"),
                        tool_status=row.get("tool_status"),
                        tool_args_json=row.get("tool_args_json"),
                        tool_result_json=row.get("tool_result_json"),
                        metadata=dict(row.get("metadata", {})),
                    )

    def cleanup(self, segments: list[SpoolSegment]) -> None:
        for segment in segments:
            try:
                segment.path.unlink(missing_ok=True)
            except OSError:
                continue


def _parse_ts(raw: str | None):
    if not raw:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
