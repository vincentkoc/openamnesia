from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class SourceRecord:
    source: str
    file_path: str
    line_number: int
    content: str
    ts: datetime | None = None
    session_hint: str | None = None
    actor: str = "user"
    tool_name: str | None = None
    tool_status: str | None = None
    tool_args_json: dict | None = None
    tool_result_json: dict | None = None
    metadata: dict = field(default_factory=dict)


class SourceConnector(Protocol):
    source_name: str

    def poll(self, state: dict) -> tuple[list[SourceRecord], dict]: ...


@dataclass(slots=True)
class ConnectorSettings:
    source_name: str
    root_path: Path
    pattern: str
