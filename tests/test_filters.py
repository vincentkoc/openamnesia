from __future__ import annotations

from datetime import UTC, datetime

from amnesia.connectors.base import SourceRecord
from amnesia.filters import (
    SourceFilterPipeline,
    make_exclude_actors_filter,
    make_exclude_contains_filter,
    make_exclude_groups_filter,
    make_include_actors_filter,
    make_include_contains_filter,
    make_include_groups_filter,
    make_since_filter,
    make_until_filter,
    parse_iso_ts,
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


def test_filter_pipeline_group_actor_and_time() -> None:
    records = [
        SourceRecord(
            source="imessage",
            file_path="x",
            line_number=1,
            content="a",
            group_hint="lauren.batten@icloud.com",
            actor="contact",
            ts=datetime(2025, 4, 1, 0, 0, tzinfo=UTC),
        ),
        SourceRecord(
            source="imessage",
            file_path="x",
            line_number=2,
            content="b",
            group_hint="otp-service",
            actor="contact",
            ts=datetime(2025, 4, 2, 0, 0, tzinfo=UTC),
        ),
        SourceRecord(
            source="imessage",
            file_path="x",
            line_number=3,
            content="c",
            group_hint="lauren.batten@icloud.com",
            actor="me",
            ts=datetime(2025, 4, 3, 0, 0, tzinfo=UTC),
        ),
    ]

    pipeline = SourceFilterPipeline()
    pipeline.add(make_include_groups_filter(["lauren"]))
    pipeline.add(make_exclude_groups_filter(["otp"]))
    pipeline.add(make_include_actors_filter(["contact"]))
    pipeline.add(make_exclude_actors_filter(["system"]))
    pipeline.add(make_since_filter(parse_iso_ts("2025-04-01T12:00:00Z")))
    pipeline.add(make_until_filter(parse_iso_ts("2025-04-02T12:00:00Z")))

    kept, dropped = pipeline.apply(records)
    assert len(kept) == 0
    assert dropped == 3

    pipeline2 = SourceFilterPipeline()
    pipeline2.add(make_include_groups_filter(["lauren"]))
    pipeline2.add(make_include_actors_filter(["me"]))
    kept2, dropped2 = pipeline2.apply(records)
    assert len(kept2) == 1
    assert kept2[0].line_number == 3
    assert dropped2 == 2
