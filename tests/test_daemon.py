from __future__ import annotations

import sqlite3
from pathlib import Path

from amnesia.config import (
    AppConfig,
    DaemonConfig,
    ExportConfig,
    HookConfig,
    SourceConfig,
    StoreConfig,
)
from amnesia.daemon import Daemon


def test_daemon_ingests_and_writes_audit(tmp_path: Path) -> None:
    ingest_dir = tmp_path / "ingest" / "terminal"
    ingest_dir.mkdir(parents=True)
    (ingest_dir / "sample.log").write_text("run tests\nDone success\n", encoding="utf-8")

    db_path = tmp_path / "amnesia.db"
    config = AppConfig(
        sources=[
            SourceConfig(name="terminal", path=str(ingest_dir), pattern="*.log", enabled=True),
        ],
        store=StoreConfig(backend="sqlite", dsn=f"sqlite:///{db_path}"),
        daemon=DaemonConfig(poll_interval_seconds=1, state_path=str(tmp_path / "state.yaml")),
        exports=ExportConfig(enabled=False),
        hooks=HookConfig(plugins=[]),
    )

    daemon = Daemon(config)
    daemon.run(once=True)

    conn = sqlite3.connect(db_path)
    events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    audits = conn.execute("SELECT COUNT(*) FROM ingest_audit").fetchone()[0]
    statuses = conn.execute("SELECT COUNT(*) FROM source_status").fetchone()[0]
    conn.close()

    assert events == 2
    assert audits == 1
    assert statuses == 1
