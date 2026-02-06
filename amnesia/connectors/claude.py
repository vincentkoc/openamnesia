from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.file_drop import FileDropConnector


@dataclass(slots=True)
class ClaudeConnector(FileDropConnector):
    settings: ConnectorSettings

    def _parse_line(self, file_path, line_number, line):
        if not line.strip():
            return None

        parsed = None
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                parsed = None

        if not isinstance(parsed, dict):
            return super()._parse_line(file_path, line_number, line)

        file_name = file_path.name
        if file_name == "history.jsonl":
            content = str(parsed.get("display", "")).strip() or line
            ts = self._parse_ts_value(parsed.get("timestamp"))
            session_hint = parsed.get("project")
            group_hint = session_hint
            return self._build_record(
                file_path=file_path,
                line_number=line_number,
                content=content,
                ts=ts,
                session_hint=session_hint,
                group_hint=group_hint,
                actor="user",
                metadata={"source_format": "claude_history"},
            )

        entry_type = parsed.get("type")
        if entry_type in {"file-history-snapshot", "file-history-diff"}:
            return None

        message = parsed.get("message")
        if isinstance(message, dict):
            role = message.get("role") or parsed.get("type") or "assistant"
            content_items = message.get("content")
            content = self._extract_text(content_items)
            ts = self._parse_ts_value(parsed.get("timestamp"))
            session_hint = parsed.get("sessionId") or file_path.stem
            group_hint = parsed.get("cwd") or session_hint
            metadata = {
                "source_format": "claude_project",
                "cwd": parsed.get("cwd"),
                "git_branch": parsed.get("gitBranch"),
                "user_type": parsed.get("userType"),
            }
            tool_record = self._extract_tool_record(
                file_path=file_path,
                line_number=line_number,
                items=content_items,
                ts=ts,
                session_hint=session_hint,
                group_hint=group_hint,
                metadata=metadata,
            )
            if tool_record is not None:
                return tool_record
            if not content:
                return None
            return self._build_record(
                file_path=file_path,
                line_number=line_number,
                content=content,
                ts=ts,
                session_hint=session_hint,
                group_hint=group_hint,
                actor=str(role),
                metadata=metadata,
            )

        return None

    def _build_record(
        self,
        *,
        file_path,
        line_number: int,
        content: str,
        ts: datetime | None,
        session_hint: str | None,
        group_hint: str | None,
        actor: str,
        metadata: dict[str, Any],
        tool_name: str | None = None,
        tool_args_json: dict | None = None,
        tool_result_json: dict | None = None,
        tool_status: str | None = None,
    ):
        payload = json.dumps(
            {
                "content": content,
                "actor": actor,
                "ts": ts.isoformat() if ts else None,
                "session_id": session_hint,
                "group_id": group_hint,
                "tool_name": tool_name,
                "tool_args": tool_args_json,
                "tool_result": tool_result_json,
                "tool_status": tool_status,
                "meta": metadata,
            },
            ensure_ascii=True,
        )
        return FileDropConnector._parse_line(self, file_path, line_number, payload)

    @staticmethod
    def _extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts).strip()
        return ""

    def _extract_tool_record(
        self,
        *,
        file_path,
        line_number: int,
        items: Any,
        ts: datetime | None,
        session_hint: str | None,
        group_hint: str | None,
        metadata: dict[str, Any],
    ):
        if not isinstance(items, list):
            return None
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                tool_name = item.get("name")
                tool_args = item.get("input") if isinstance(item.get("input"), dict) else None
                return self._build_record(
                    file_path=file_path,
                    line_number=line_number,
                    content=tool_name or "tool_use",
                    ts=ts,
                    session_hint=session_hint,
                    group_hint=group_hint,
                    actor="assistant",
                    metadata={**metadata, "entry_type": "tool_use"},
                    tool_name=tool_name,
                    tool_args_json=tool_args,
                    tool_status="called",
                )
            if item.get("type") == "tool_result":
                is_error = bool(item.get("is_error"))
                status = "error" if is_error else "ok"
                return self._build_record(
                    file_path=file_path,
                    line_number=line_number,
                    content="tool_result",
                    ts=ts,
                    session_hint=session_hint,
                    group_hint=group_hint,
                    actor="tool",
                    metadata={**metadata, "entry_type": "tool_result"},
                    tool_result_json={
                        "tool_use_id": item.get("tool_use_id"),
                        "content": item.get("content"),
                        "is_error": is_error,
                    },
                    tool_status=status,
                )
        return None

    @staticmethod
    def _parse_ts_value(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            seconds = float(value)
            if seconds > 1e12:
                seconds = seconds / 1000.0
            return datetime.fromtimestamp(seconds, tz=UTC)
        if isinstance(value, str):
            raw = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                try:
                    seconds = float(raw)
                except ValueError:
                    return None
                if seconds > 1e12:
                    seconds = seconds / 1000.0
                return datetime.fromtimestamp(seconds, tz=UTC)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        return None
