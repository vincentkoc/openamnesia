from __future__ import annotations

from pathlib import Path

from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.imessage import IMessageConnector


def test_imessage_connector_parses_chat_and_group_stats(tmp_path: Path) -> None:
    src_dir = tmp_path / "imessage"
    src_dir.mkdir(parents=True)
    sample = src_dir / "chat.jsonl"
    sample.write_text(
        '{"ts":"2026-02-06T10:00:00Z","chat_id":"chat-a","sender":"me","text":"hi"}\n'
        '{"ts":"2026-02-06T10:00:05Z","chat_id":"chat-a","sender":"contact","text":"hey"}\n',
        encoding="utf-8",
    )

    connector = IMessageConnector(
        settings=ConnectorSettings(
            source_name="imessage",
            root_path=src_dir,
            pattern="*.jsonl",
            options={"mode": "jsonl"},
        )
    )

    result = connector.poll(state={})
    assert len(result.records) == 2
    assert result.records[0].group_hint == "chat-a"
    assert result.stats.groups_seen == 1
    assert result.stats.item_counts_by_group["chat-a"] == 2
