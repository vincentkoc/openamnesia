from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from amnesia.connectors.base import ConnectorSettings, SourceRecord


@dataclass(slots=True)
class FileDropConnector:
    settings: ConnectorSettings

    @property
    def source_name(self) -> str:
        return self.settings.source_name

    def poll(self, state: dict) -> tuple[list[SourceRecord], dict]:
        records: list[SourceRecord] = []
        new_state = dict(state)

        root = self.settings.root_path
        if not root.exists():
            return records, new_state

        for file_path in sorted(root.glob(self.settings.pattern)):
            if not file_path.is_file():
                continue

            file_key = str(file_path.resolve())
            last_line = int(new_state.get(file_key, 0))
            processed = 0

            with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                for idx, line in enumerate(fh, start=1):
                    if idx <= last_line:
                        continue
                    record = self._parse_line(file_path, idx, line.rstrip("\n"))
                    if record is not None:
                        records.append(record)
                    processed = idx

            if processed > 0:
                new_state[file_key] = processed

        return records, new_state

    def _parse_line(self, file_path: Path, line_number: int, line: str) -> SourceRecord | None:
        if not line.strip():
            return None

        parsed = None
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                parsed = None

        ts = None
        session_hint = None
        actor = "user"
        content = line
        tool_name = None
        tool_status = None
        tool_args_json = None
        tool_result_json = None
        metadata = {"path": str(file_path)}

        if isinstance(parsed, dict):
            content = str(parsed.get("content", line))
            actor = str(parsed.get("actor", "user"))
            session_hint = parsed.get("session_id")
            tool_name = parsed.get("tool_name")
            tool_status = parsed.get("tool_status")
            tool_args_json = parsed.get("tool_args")
            tool_result_json = parsed.get("tool_result")
            metadata.update(parsed.get("meta", {}))

            ts_raw = parsed.get("ts")
            if isinstance(ts_raw, str):
                ts = self._parse_ts(ts_raw)

        return SourceRecord(
            source=self.source_name,
            file_path=str(file_path),
            line_number=line_number,
            content=content,
            ts=ts,
            session_hint=session_hint,
            actor=actor,
            tool_name=tool_name,
            tool_status=tool_status,
            tool_args_json=tool_args_json,
            tool_result_json=tool_result_json,
            metadata=metadata,
        )

    @staticmethod
    def _parse_ts(value: str) -> datetime | None:
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            return None

    @staticmethod
    def stable_session_id(seed: str) -> str:
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
