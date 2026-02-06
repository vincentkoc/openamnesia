"""Source record filtering hooks and built-in filters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from amnesia.connectors.base import SourceRecord

RecordFilter = Callable[[SourceRecord], bool]


@dataclass(slots=True)
class SourceFilterPipeline:
    filters: list[RecordFilter] = field(default_factory=list)

    def add(self, record_filter: RecordFilter) -> None:
        self.filters.append(record_filter)

    def apply(self, records: list[SourceRecord]) -> tuple[list[SourceRecord], int]:
        if not self.filters:
            return records, 0

        kept: list[SourceRecord] = []
        dropped = 0

        for record in records:
            if all(predicate(record) for predicate in self.filters):
                kept.append(record)
            else:
                dropped += 1

        return kept, dropped


def make_include_contains_filter(needles: list[str]) -> RecordFilter:
    lowered = _normalized_terms(needles)

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        content = record.content.lower()
        return _contains_any(content, lowered)

    return _predicate


def make_exclude_contains_filter(needles: list[str]) -> RecordFilter:
    lowered = _normalized_terms(needles)

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        content = record.content.lower()
        return not _contains_any(content, lowered)

    return _predicate


def make_include_groups_filter(needles: list[str]) -> RecordFilter:
    lowered = _normalized_terms(needles)

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        value = (record.group_hint or record.session_hint or "").lower()
        return _contains_any(value, lowered)

    return _predicate


def make_exclude_groups_filter(needles: list[str]) -> RecordFilter:
    lowered = _normalized_terms(needles)

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        value = (record.group_hint or record.session_hint or "").lower()
        return not _contains_any(value, lowered)

    return _predicate


def make_include_actors_filter(needles: list[str]) -> RecordFilter:
    lowered = _normalized_terms(needles)

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        return _contains_any(record.actor.lower(), lowered)

    return _predicate


def make_exclude_actors_filter(needles: list[str]) -> RecordFilter:
    lowered = _normalized_terms(needles)

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        return not _contains_any(record.actor.lower(), lowered)

    return _predicate


def make_since_filter(since: datetime | None) -> RecordFilter:
    def _predicate(record: SourceRecord) -> bool:
        if since is None:
            return True
        if record.ts is None:
            return False
        return record.ts >= since

    return _predicate


def make_until_filter(until: datetime | None) -> RecordFilter:
    def _predicate(record: SourceRecord) -> bool:
        if until is None:
            return True
        if record.ts is None:
            return False
        return record.ts <= until

    return _predicate


def parse_iso_ts(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _normalized_terms(values: list[str]) -> list[str]:
    return [item.lower().strip() for item in values if item and item.strip()]


def _contains_any(value: str, needles: list[str]) -> bool:
    return any(needle in value for needle in needles)
