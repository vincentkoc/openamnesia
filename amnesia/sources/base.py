"""Normalized source API contracts and base IO classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(slots=True)
class BaseInput:
    source: str
    state: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BaseOutput:
    source: str
    ts: datetime
    state: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


class SourceOperation(Protocol):
    def run(self, input_data: BaseInput) -> BaseOutput:
        ...
