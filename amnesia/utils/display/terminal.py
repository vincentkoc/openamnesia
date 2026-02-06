"""Simple terminal summaries for ingestion runs."""

from __future__ import annotations

import json

from amnesia.api_objects.types import IngestionRunSummary


def print_run_summary(summary: IngestionRunSummary) -> None:
    totals = summary.to_dict()["totals"]
    print(
        "Ingestion complete:"
        f" records_seen={totals['records_seen']}"
        f" records_ingested={totals['records_ingested']}"
        f" events={totals['events']}"
        f" sessions={totals['sessions']}"
        f" moments={totals['moments']}"
        f" skills={totals['skills']}"
        f" duration={summary.duration_seconds:.2f}s"
    )
    for src in summary.source_summaries:
        msg = (
            f"  - {src.source:<10} status={src.status:<9}"
            f" seen={src.records_seen:<4} ingested={src.records_ingested:<4}"
            f" events={src.inserted_events:<4} sessions={src.inserted_sessions:<4}"
            f" moments={src.inserted_moments:<4} skills={src.inserted_skills:<4}"
        )
        if src.error_message:
            msg += f" error={src.error_message}"
        print(msg)


def print_run_summary_json(summary: IngestionRunSummary) -> None:
    print(json.dumps(summary.to_dict(), ensure_ascii=True))

