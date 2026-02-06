"""Helpers for consistent source poll event payloads."""

from __future__ import annotations

from amnesia.api_objects.types import (
    SourcePollCompletedEvent,
    SourcePollErrorEvent,
    SourcePollStartedEvent,
)
from amnesia.internal.events import EventBus


def emit_source_poll_started(bus: EventBus, *, source: str, state_keys: int = 0) -> None:
    payload = SourcePollStartedEvent(source=source, state_keys=state_keys)
    bus.emit("source.poll.started", **payload.to_dict())


def emit_source_poll_completed(
    bus: EventBus,
    *,
    source: str,
    items_seen: int,
    items_ingested: int,
    items_filtered: int,
    groups_seen: int,
) -> None:
    payload = SourcePollCompletedEvent(
        source=source,
        items_seen=items_seen,
        items_ingested=items_ingested,
        items_filtered=items_filtered,
        groups_seen=groups_seen,
    )
    bus.emit("source.poll.completed", **payload.to_dict())


def emit_source_poll_error(bus: EventBus, *, source: str, error: str) -> None:
    payload = SourcePollErrorEvent(source=source, error=error)
    bus.emit("source.poll.error", **payload.to_dict())
