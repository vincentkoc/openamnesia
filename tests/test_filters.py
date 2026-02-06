from __future__ import annotations

from amnesia.connectors.base import SourceRecord
from amnesia.filters import (
    SourceFilterPipeline,
    make_exclude_contains_filter,
    make_include_contains_filter,
)


def test_filter_pipeline_include_exclude() -> None:
    records = [
        SourceRecord(source="imessage", file_path="x", line_number=1, content="Dinner at 7"),
        SourceRecord(source="imessage", file_path="x", line_number=2, content="Buy milk"),
        SourceRecord(source="imessage", file_path="x", line_number=3, content="dinner tomorrow"),
    ]

    pipeline = SourceFilterPipeline()
    pipeline.add(make_include_contains_filter(["dinner"]))
    pipeline.add(make_exclude_contains_filter(["tomorrow"]))

    kept, dropped = pipeline.apply(records)
    assert len(kept) == 1
    assert kept[0].content == "Dinner at 7"
    assert dropped == 2
