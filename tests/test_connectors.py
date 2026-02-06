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

    records1, state1 = connector.poll(state={})
    assert len(records1) == 2
    assert state1[str(sample.resolve())] == 2

    records2, state2 = connector.poll(state=state1)
    assert len(records2) == 0
    assert state2 == state1
