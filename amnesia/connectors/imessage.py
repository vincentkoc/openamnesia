from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from amnesia.api_objects.types import SourceState, SourceStats
from amnesia.connectors.base import (
    ConnectorSettings,
    SourcePollResult,
    SourceRecord,
)
from amnesia.sources.imessage.imessage import read_messages
from amnesia.sources.imessage.types import IMessageReadInput


@dataclass(slots=True)
class IMessageConnector:
    settings: ConnectorSettings

    @property
    def source_name(self) -> str:
        return self.settings.source_name

    def poll(self, state: dict[str, Any]) -> SourcePollResult:
        mode = str(self.settings.options.get("mode", "sqlite")).strip().lower()
        if mode == "jsonl":
            return self._poll_jsonl(state)
        return self._poll_sqlite(state)

    def _poll_sqlite(self, state: dict[str, Any]) -> SourcePollResult:
        last_rowid = int(state.get("last_rowid", 0) or 0)
        db_path = str(self.settings.options.get("db_path", ""))
        if db_path:
            db_path = str(Path(db_path).expanduser())
        limit = int(self.settings.options.get("limit", 500) or 500)

        output = read_messages(
            IMessageReadInput(
                source=self.source_name,
                state=state,
                options=self.settings.options,
                db_path=db_path,
                min_rowid_exclusive=last_rowid,
                limit=limit,
            )
        )

        records: list[SourceRecord] = []
        group_counter: Counter[str] = Counter()
        db_meta = {"db_path": output.meta.get("db_path"), "db_missing": output.meta.get("missing")}

        for message in output.messages:
            chat_id = message.chat_id or "unknown_chat"
            group_counter[chat_id] += 1
            records.append(
                SourceRecord(
                    source=self.source_name,
                    file_path=str(output.meta.get("db_path") or ""),
                    line_number=message.rowid,
                    content=message.text,
                    ts=message.ts,
                    session_hint=chat_id,
                    group_hint=chat_id,
                    actor=message.sender,
                    metadata={
                        **db_meta,
                        "rowid": message.rowid,
                        "service": message.service,
                        "contact": message.contact,
                    },
                )
            )

        stats = SourceStats(
            items_seen=len(records),
            groups_seen=len(group_counter),
            item_counts_by_group=dict(group_counter),
        )
        return SourcePollResult.from_contracts(
            records=records,
            state=SourceState(values=output.state),
            stats=stats,
        )

    def _poll_jsonl(self, state: dict[str, Any]) -> SourcePollResult:
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

        for file_path in sorted(root.glob(self.settings.pattern)):
            if not file_path.is_file():
                continue

            file_key = str(file_path.resolve())
            last_line = int(new_state.values.get(file_key, 0) or 0)
            processed = 0

            with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                for idx, line in enumerate(fh, start=1):
                    if idx <= last_line:
                        continue
                    record = self._parse_line_jsonl(file_path, idx, line.rstrip("\n"))
                    if record is not None:
                        records.append(record)
                        group_key = record.group_hint or file_path.stem
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

    def _parse_line_jsonl(
        self, file_path: Path, line_number: int, line: str
    ) -> SourceRecord | None:
        if not line.strip():
            return None

        payload = None
        if line.startswith("{"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                payload = None

        if not isinstance(payload, dict):
            return SourceRecord(
                source=self.source_name,
                file_path=str(file_path),
                line_number=line_number,
                content=line,
                actor="unknown",
                session_hint=file_path.stem,
                group_hint=file_path.stem,
                metadata={"path": str(file_path), "format": "raw_line"},
            )

        text = str(payload.get("text") or payload.get("content") or "")
        if not text.strip():
            return None

        chat_id = str(payload.get("chat_id") or payload.get("group_id") or file_path.stem)
        sender = str(payload.get("sender") or payload.get("actor") or "unknown")

        ts = None
        ts_raw = payload.get("ts")
        if isinstance(ts_raw, str):
            ts = self._parse_ts(ts_raw)
        elif isinstance(ts_raw, (int, float)):
            ts = datetime.fromtimestamp(float(ts_raw), tz=UTC)

        metadata = {
            "path": str(file_path),
            "contact": payload.get("name") or payload.get("contact"),
            "service": payload.get("service") or "imessage",
        }

        return SourceRecord(
            source=self.source_name,
            file_path=str(file_path),
            line_number=line_number,
            content=text,
            ts=ts,
            session_hint=chat_id,
            group_hint=chat_id,
            actor=sender,
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
