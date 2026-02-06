"""Typed inputs/outputs for iMessage source operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from amnesia.sources.base import BaseInput, BaseOutput


@dataclass(slots=True)
class IMessageReadInput(BaseInput):
    db_path: str = ""
    min_rowid_exclusive: int = 0
    limit: int = 500


@dataclass(slots=True)
class IMessageMessage:
    rowid: int
    ts: datetime | None
    chat_id: str
    sender: str
    text: str
    service: str | None = None
    contact: str | None = None


@dataclass(slots=True)
class IMessageReadOutput(BaseOutput):
    messages: list[IMessageMessage] = field(default_factory=list)
    max_rowid_seen: int = 0
