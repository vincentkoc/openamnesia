from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.file_drop import FileDropConnector


@dataclass(slots=True)
class CodexConnector(FileDropConnector):
    settings: ConnectorSettings
    _session_groups: dict[str, str] = field(default_factory=dict)
    _file_groups: dict[str, str] = field(default_factory=dict)

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
            content = str(parsed.get("text", "")).strip() or line
            ts = self._parse_ts_value(parsed.get("ts"))
            session_hint = parsed.get("session_id")
            group_hint = None
            if session_hint:
                group_hint = self._session_groups.get(str(session_hint))
            return self._build_record(
                file_path=file_path,
                line_number=line_number,
                content=content,
                ts=ts,
                session_hint=session_hint,
                group_hint=group_hint,
                actor="user",
                metadata={"source_format": "codex_history"},
            )

        entry_type = parsed.get("type")
        if entry_type == "session_meta":
            payload = parsed.get("payload") or {}
            if isinstance(payload, dict):
                session_id = payload.get("id")
                group = payload.get("cwd")
                git = payload.get("git") if isinstance(payload.get("git"), dict) else None
                if not group and git:
                    group = git.get("repository_url") or git.get("branch")
                group = _normalize_group(group)
                if group:
                    self._file_groups[str(file_path)] = str(group)
                if session_id and group:
                    self._session_groups[str(session_id)] = str(group)
            return None

        if entry_type == "response_item":
            payload = parsed.get("payload") or {}
            if isinstance(payload, dict):
                payload_type = payload.get("type")
                ts = self._parse_ts_value(parsed.get("timestamp") or payload.get("timestamp"))
                session_hint = payload.get("id") or file_path.stem
                group_hint = self._session_groups.get(str(session_hint))
                if group_hint is None:
                    group_hint = self._file_groups.get(str(file_path))

                if payload_type == "message":
                    role = payload.get("role") or "assistant"
                    content = self._extract_text(payload.get("content"))
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
                        metadata={
                            "source_format": "codex_session",
                            "entry_type": entry_type,
                        },
                    )

                if payload_type == "function_call":
                    tool_args = self._parse_json_payload(payload.get("arguments"))
                    tool_name = payload.get("name")
                    content = tool_name or "tool_call"
                    return self._build_record(
                        file_path=file_path,
                        line_number=line_number,
                        content=content,
                        ts=ts,
                        session_hint=session_hint,
                        group_hint=group_hint,
                        actor="assistant",
                        metadata={
                            "source_format": "codex_session",
                            "entry_type": "function_call",
                        },
                        tool_name=tool_name,
                        tool_args_json=tool_args,
                        tool_status="called",
                    )

                if payload_type == "function_call_output":
                    output = payload.get("output")
                    exit_code = self._parse_exit_code(output)
                    status = "ok" if exit_code == 0 else "error"
                    return self._build_record(
                        file_path=file_path,
                        line_number=line_number,
                        content="tool_output",
                        ts=ts,
                        session_hint=session_hint,
                        group_hint=group_hint,
                        actor="tool",
                        metadata={
                            "source_format": "codex_session",
                            "entry_type": "function_call_output",
                            "exit_code": exit_code,
                        },
                        tool_name=None,
                        tool_result_json={"output": output, "exit_code": exit_code},
                        tool_status=status,
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
                    text = item.get("text") or item.get("input_text") or item.get("output_text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts).strip()
        return ""

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

    @staticmethod
    def _parse_json_payload(value: Any) -> dict | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {"raw": value}
        return {"raw": str(value)}

    @staticmethod
    def _parse_exit_code(output: Any) -> int | None:
        if not isinstance(output, str):
            return None
        marker = "Exit code:"
        if marker not in output:
            return None
        try:
            tail = output.split(marker, 1)[1].strip()
            return int(tail.split()[0])
        except (IndexError, ValueError):
            return None


def _normalize_group(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith("http"):
        tail = raw.rstrip("/").split("/")[-1]
        if tail.endswith(".git"):
            tail = tail[:-4]
        return tail or raw
    return raw.rstrip("/").split("/")[-1] or raw
