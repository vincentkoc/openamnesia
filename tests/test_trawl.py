from __future__ import annotations

from pathlib import Path

from amnesia.ingest.trawl import IncrementalFileTrawler, TrawlState


def test_incremental_trawler_reads_only_new_content(tmp_path: Path) -> None:
    src_dir = tmp_path / "terminal"
    src_dir.mkdir(parents=True)
    log_file = src_dir / "a.log"
    log_file.write_text('{"content":"one"}\n{"content":"two"}\n', encoding="utf-8")

    trawler = IncrementalFileTrawler(source_name="terminal", root_path=src_dir, pattern="*.log")
    state = TrawlState()
    first = list(trawler.iter_new_records(state))
    assert len(first) == 2

    second = list(trawler.iter_new_records(state))
    assert len(second) == 0

    with log_file.open("a", encoding="utf-8") as fh:
        fh.write('{"content":"three"}\n')
    third = list(trawler.iter_new_records(state))
    assert len(third) == 1
    assert third[0].content == "three"
