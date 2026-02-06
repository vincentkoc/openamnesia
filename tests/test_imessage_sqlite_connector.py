from __future__ import annotations

import sqlite3
from pathlib import Path

from amnesia.connectors.base import ConnectorSettings
from amnesia.connectors.imessage import IMessageConnector


def _create_test_chat_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE message (
              rowid INTEGER PRIMARY KEY,
              text TEXT,
              date INTEGER,
              is_from_me INTEGER,
              service TEXT,
              handle_id INTEGER,
              cache_roomnames TEXT
            );
            CREATE TABLE handle (
              rowid INTEGER PRIMARY KEY,
              id TEXT
            );
            CREATE TABLE chat (
              rowid INTEGER PRIMARY KEY,
              chat_identifier TEXT,
              display_name TEXT
            );
            CREATE TABLE chat_message_join (
              chat_id INTEGER,
              message_id INTEGER
            );
            """
        )
        conn.execute("INSERT INTO handle (rowid, id) VALUES (?, ?)", (1, "+15551234567"))
        conn.execute(
            "INSERT INTO chat (rowid, chat_identifier, display_name) VALUES (?, ?, ?)",
            (1, "chat-group", "Group A"),
        )
        conn.execute(
            """
            INSERT INTO message (rowid, text, date, is_from_me, service, handle_id, cache_roomnames)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "Hello from sqlite", 1000, 1, "iMessage", 1, None),
        )
        conn.execute("INSERT INTO chat_message_join (chat_id, message_id) VALUES (?, ?)", (1, 1))
        conn.commit()
    finally:
        conn.close()


def test_imessage_connector_sqlite_mode_reads_and_tracks_state(tmp_path: Path) -> None:
    db_path = tmp_path / "chat.db"
    _create_test_chat_db(db_path)

    connector = IMessageConnector(
        settings=ConnectorSettings(
            source_name="imessage",
            root_path=tmp_path,
            pattern="*.jsonl",
            options={"mode": "sqlite", "db_path": str(db_path), "limit": 100},
        )
    )

    first = connector.poll(state={})
    assert len(first.records) == 1
    assert first.records[0].content == "Hello from sqlite"
    assert first.records[0].group_hint == "chat-group"
    assert first.state["last_rowid"] == 1

    second = connector.poll(state=first.state)
    assert len(second.records) == 0
    assert second.state["last_rowid"] == 1
