from __future__ import annotations

from pathlib import Path

from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.file_drop import FileDropConnector


def test_file_drop_connector_tracks_line_offset(tmp_path: Path) -> None:
    src_dir = tmp_path / "cursor"
    src_dir.mkdir(parents=True)
    sample = src_dir / "sample.jsonl"
    sample.write_text('{"content":"one"}\n{"content":"two"}\n', encoding="utf-8")

    connector = FileDropConnector(
        settings=ConnectorSettings(source_name="cursor", root_path=src_dir, pattern="*.jsonl")
    )

    result1 = connector.poll(state={})
    assert len(result1.records) == 2
    assert result1.state[str(sample.resolve())] == 2
    assert result1.stats.items_seen == 2
    assert result1.stats.groups_seen == 1

    result2 = connector.poll(state=result1.state)
    assert len(result2.records) == 0
    assert result2.state == result1.state
