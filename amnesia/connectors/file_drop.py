from __future__ import annotations

import fnmatch
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from amnesia.api_objects.types import SourceState, SourceStats
from amnesia.connectors.base import (
    ConnectorSettings,
    SourcePollResult,
    SourceRecord,
)


@dataclass(slots=True)
class FileDropConnector:
    settings: ConnectorSettings

    @property
    def source_name(self) -> str:
        return self.settings.source_name

    def poll(self, state: dict) -> SourcePollResult:
        records: list[SourceRecord] = []
        new_state = SourceState(values=dict(state))
        group_counter: Counter[str] = Counter()

        root = self.settings.root_path
        if not root.exists():
            return SourcePollResult.from_contracts(
                records=records,
                state=new_state,
                stats=SourceStats(),
            )

        for file_path in self._iter_files(root):
            if not file_path.is_file():
                continue

            file_key = str(file_path.resolve())
            last_line = int(new_state.values.get(file_key, 0))
            processed = 0

            with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                for idx, line in enumerate(fh, start=1):
                    if idx <= last_line:
                        continue
                    record = self._parse_line(file_path, idx, line.rstrip("\n"))
                    if record is not None:
                        records.append(record)
                        group_key = record.group_hint or record.session_hint or file_key
                        group_counter[group_key] += 1
                    processed = idx

            if processed > 0:
                new_state.values[file_key] = processed

        stats = SourceStats(
            items_seen=len(records),
            groups_seen=len(group_counter),
            item_counts_by_group=dict(group_counter),
        )
        return SourcePollResult.from_contracts(records=records, state=new_state, stats=stats)

    def _iter_files(self, root: Path) -> list[Path]:
        include_globs = self.settings.options.get("include_globs")
        exclude_globs = self.settings.options.get("exclude_globs") or []
        include_list: list[str] = []
        if isinstance(include_globs, (list, tuple)):
            include_list = [str(item) for item in include_globs if str(item).strip()]
        paths: list[Path] = []
        if include_list:
            for pattern in include_list:
                paths.extend(root.glob(pattern))
        else:
            paths.extend(root.glob(self.settings.pattern))

        excluded: list[Path] = []
        for path in paths:
            if not exclude_globs:
                excluded.append(path)
                continue
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                rel = str(path)
            if any(fnmatch.fnmatch(rel, str(pattern)) for pattern in exclude_globs):
                continue
            excluded.append(path)

        unique = sorted({path.resolve() for path in excluded})
        return unique

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
        group_hint = None
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
            group_hint = parsed.get("group_id") or parsed.get("chat_id")
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
            group_hint=group_hint,
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
