"""Incremental filesystem trawling for high-volume ingestion."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from amnesia.connectors.base import SourceRecord


@dataclass(slots=True)
class FileCheckpoint:
    path: str
    offset: int
    size: int
    mtime_ns: int
    inode: int
    digest: str


@dataclass(slots=True)
class TrawlState:
    files: dict[str, FileCheckpoint] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TrawlState:
        files_raw = payload.get("files", {})
        files: dict[str, FileCheckpoint] = {}
        if isinstance(files_raw, dict):
            for path, raw in files_raw.items():
                if not isinstance(raw, dict):
                    continue
                files[path] = FileCheckpoint(
                    path=path,
                    offset=int(raw.get("offset", 0)),
                    size=int(raw.get("size", 0)),
                    mtime_ns=int(raw.get("mtime_ns", 0)),
                    inode=int(raw.get("inode", 0)),
                    digest=str(raw.get("digest", "")),
                )
        return cls(files=files)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": {
                path: {
                    "offset": cp.offset,
                    "size": cp.size,
                    "mtime_ns": cp.mtime_ns,
                    "inode": cp.inode,
                    "digest": cp.digest,
                }
                for path, cp in self.files.items()
            }
        }


@dataclass(slots=True)
class TrawlStats:
    files_scanned: int = 0
    files_changed: int = 0
    bytes_read: int = 0
    records_emitted: int = 0


class IncrementalFileTrawler:
    def __init__(
        self,
        *,
        source_name: str,
        root_path: Path,
        pattern: str = "**/*",
        max_line_bytes: int = 1024 * 1024,
    ) -> None:
        self.source_name = source_name
        self.root_path = root_path
        self.pattern = pattern
        self.max_line_bytes = max_line_bytes

    def iter_new_records(
        self,
        state: TrawlState,
        *,
        limit_records: int | None = None,
    ) -> Iterator[SourceRecord]:
        emitted = 0
        for file_path in self._iter_candidate_files():
            cp = state.files.get(str(file_path))
            stat = file_path.stat()
            inode = int(getattr(stat, "st_ino", 0))
            mtime_ns = int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9)))
            size = int(stat.st_size)

            start_offset = 0
            if cp is not None and cp.inode == inode and cp.size <= size:
                start_offset = cp.offset

            if start_offset >= size:
                state.files[str(file_path)] = self._checkpoint_for_file(
                    file_path=file_path,
                    offset=size,
                    size=size,
                    mtime_ns=mtime_ns,
                    inode=inode,
                )
                continue

            with file_path.open("rb") as fh:
                fh.seek(start_offset)
                line_number = 0
                while True:
                    raw_line = fh.readline(self.max_line_bytes + 1)
                    if not raw_line:
                        break
                    if len(raw_line) > self.max_line_bytes:
                        continue
                    line_number += 1
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                    record = self._parse_line(file_path, line_number + start_offset, line)
                    if record is None:
                        continue
                    emitted += 1
                    yield record
                    if limit_records is not None and emitted >= limit_records:
                        state.files[str(file_path)] = self._checkpoint_for_file(
                            file_path=file_path,
                            offset=fh.tell(),
                            size=size,
                            mtime_ns=mtime_ns,
                            inode=inode,
                        )
                        return

                state.files[str(file_path)] = self._checkpoint_for_file(
                    file_path=file_path,
                    offset=fh.tell(),
                    size=size,
                    mtime_ns=mtime_ns,
                    inode=inode,
                )

    def collect_stats(self, state_before: TrawlState, state_after: TrawlState) -> TrawlStats:
        files_scanned = len(state_after.files)
        files_changed = 0
        bytes_read = 0
        for path, after in state_after.files.items():
            before = state_before.files.get(path)
            before_offset = before.offset if before is not None else 0
            delta = max(0, after.offset - before_offset)
            if delta > 0:
                files_changed += 1
                bytes_read += delta
        return TrawlStats(
            files_scanned=files_scanned,
            files_changed=files_changed,
            bytes_read=bytes_read,
        )

    def _iter_candidate_files(self) -> list[Path]:
        if not self.root_path.exists():
            return []
        return sorted(path for path in self.root_path.glob(self.pattern) if path.is_file())

    def _parse_line(self, file_path: Path, line_number: int, line: str) -> SourceRecord | None:
        if not line.strip():
            return None

        parsed: dict[str, Any] | None = None
        if line.startswith("{"):
            try:
                value = json.loads(line)
                parsed = value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                parsed = None

        ts = None
        session_hint = None
        group_hint = None
        actor = "user"
        content = line
        tool_name = None
        tool_status = None
        tool_args_json = None
        tool_result_json = None
        metadata: dict[str, Any] = {"path": str(file_path), "ingest": "trawl"}

        if isinstance(parsed, dict):
            content = str(parsed.get("content", line))
            actor = str(parsed.get("actor", "user"))
            session_hint = parsed.get("session_id")
            group_hint = parsed.get("group_id") or parsed.get("chat_id")
            tool_name = parsed.get("tool_name")
            tool_status = parsed.get("tool_status")
            tool_args_json = parsed.get("tool_args")
            tool_result_json = parsed.get("tool_result")
            if isinstance(parsed.get("meta"), dict):
                metadata.update(parsed["meta"])
            ts_raw = parsed.get("ts")
            if isinstance(ts_raw, str):
                ts = _parse_ts(ts_raw)

        return SourceRecord(
            source=self.source_name,
            file_path=str(file_path),
            line_number=int(line_number),
            content=content,
            ts=ts,
            session_hint=session_hint,
            group_hint=group_hint,
            actor=actor,
            tool_name=tool_name,
            tool_status=tool_status,
            tool_args_json=tool_args_json,
            tool_result_json=tool_result_json,
            metadata=metadata,
        )

    @staticmethod
    def _checkpoint_for_file(
        *,
        file_path: Path,
        offset: int,
        size: int,
        mtime_ns: int,
        inode: int,
    ) -> FileCheckpoint:
        digest_seed = f"{file_path}:{inode}:{size}:{mtime_ns}:{offset}"
        digest = hashlib.sha256(digest_seed.encode("utf-8")).hexdigest()[:16]
        return FileCheckpoint(
            path=str(file_path),
            offset=offset,
            size=size,
            mtime_ns=mtime_ns,
            inode=inode,
            digest=digest,
        )


def _parse_ts(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
