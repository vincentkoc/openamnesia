"""Source record filtering hooks and built-in filters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

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
    lowered = [item.lower() for item in needles if item.strip()]

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        content = record.content.lower()
        return any(needle in content for needle in lowered)

    return _predicate


def make_exclude_contains_filter(needles: list[str]) -> RecordFilter:
    lowered = [item.lower() for item in needles if item.strip()]

    def _predicate(record: SourceRecord) -> bool:
        if not lowered:
            return True
        content = record.content.lower()
        return not any(needle in content for needle in lowered)

    return _predicate
