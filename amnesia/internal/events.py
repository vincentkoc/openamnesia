"""Internal event bus for source/runtime observability."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from amnesia.models import utc_now


@dataclass(slots=True)
class InternalEvent:
    topic: str
    ts: datetime
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list] = defaultdict(list)
        self._events: list[InternalEvent] = []

    def subscribe(self, topic: str, callback) -> None:
        self._subscribers[topic].append(callback)

    def emit(self, topic: str, **payload: Any) -> InternalEvent:
        event = InternalEvent(topic=topic, ts=utc_now(), payload=payload)
        self._events.append(event)

        for callback in self._subscribers.get(topic, []):
            callback(event)
        for callback in self._subscribers.get("*", []):
            callback(event)

        return event

    def recent(self, limit: int = 100) -> list[InternalEvent]:
        if limit <= 0:
            return []
        return self._events[-limit:]
