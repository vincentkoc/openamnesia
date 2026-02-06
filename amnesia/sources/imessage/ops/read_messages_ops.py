"""SQLite read operation for iMessage chat database."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from amnesia.models import utc_now
from amnesia.sources.imessage.helpers import parse_apple_message_date, resolve_imessage_db_path
from amnesia.sources.imessage.types import IMessageMessage, IMessageReadInput, IMessageReadOutput


class ReadMessagesOp:
    def run(self, input_data: IMessageReadInput) -> IMessageReadOutput:
        db_path = resolve_imessage_db_path(input_data.db_path)
        if not db_path.exists():
            return IMessageReadOutput(
                source=input_data.source,
                ts=utc_now(),
                state=input_data.state,
                meta={"db_path": str(db_path), "missing": True},
                messages=[],
                max_rowid_seen=input_data.min_rowid_exclusive,
            )

        conn, opened_path = self._open_readable_connection(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                  m.rowid AS rowid,
                  m.text AS text,
                  m.date AS message_date,
                  m.is_from_me AS is_from_me,
                  m.service AS service,
                  h.id AS handle_id,
                  COALESCE(
                    c.chat_identifier,
                    c.display_name,
                    m.cache_roomnames,
                    h.id,
                    'unknown_chat'
                  ) AS chat_id
                FROM message m
                LEFT JOIN handle h ON h.rowid = m.handle_id
                LEFT JOIN chat_message_join cmj ON cmj.message_id = m.rowid
                LEFT JOIN chat c ON c.rowid = cmj.chat_id
                WHERE m.rowid > ?
                  AND m.text IS NOT NULL
                  AND TRIM(m.text) != ''
                ORDER BY m.rowid ASC
                LIMIT ?
                """,
                (input_data.min_rowid_exclusive, input_data.limit),
            ).fetchall()
        finally:
            conn.close()

        messages: list[IMessageMessage] = []
        max_rowid = input_data.min_rowid_exclusive

        for row in rows:
            rowid = int(row["rowid"])
            max_rowid = max(max_rowid, rowid)
            sender = "me" if int(row["is_from_me"] or 0) == 1 else "contact"
            messages.append(
                IMessageMessage(
                    rowid=rowid,
                    ts=parse_apple_message_date(row["message_date"]),
                    chat_id=str(row["chat_id"]),
                    sender=sender,
                    text=str(row["text"]),
                    service=str(row["service"]) if row["service"] is not None else None,
                    contact=str(row["handle_id"]) if row["handle_id"] is not None else None,
                )
            )

        state = dict(input_data.state)
        state["last_rowid"] = max_rowid

        return IMessageReadOutput(
            source=input_data.source,
            ts=utc_now(),
            state=state,
            meta={"db_path": str(opened_path), "source_db_path": str(db_path), "missing": False},
            messages=messages,
            max_rowid_seen=max_rowid,
        )

    def _open_readable_connection(self, db_path: Path) -> tuple[sqlite3.Connection, Path]:
        try:
            return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True), db_path
        except sqlite3.DatabaseError:
            # Fallback path: copy DB (+ optional wal/shm) to temp and open copy.
            temp_root = Path(tempfile.mkdtemp(prefix="amnesia_imessage_"))
            temp_db = temp_root / "chat.db"
            try:
                shutil.copy2(db_path, temp_db)
                wal = db_path.with_name(db_path.name + "-wal")
                shm = db_path.with_name(db_path.name + "-shm")
                if wal.exists():
                    shutil.copy2(wal, temp_root / wal.name)
                if shm.exists():
                    shutil.copy2(shm, temp_root / shm.name)
                return sqlite3.connect(f"file:{temp_db}?mode=ro", uri=True), temp_db
            except Exception as copy_exc:
                raise RuntimeError(
                    "Unable to read iMessage chat.db. "
                    "Grant Terminal/CLI Full Disk Access in macOS Privacy settings, "
                    "or use imessage options.mode=jsonl for exports."
                ) from copy_exc
