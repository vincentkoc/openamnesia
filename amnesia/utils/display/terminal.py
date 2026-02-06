"""Simple terminal summaries for ingestion runs."""

from __future__ import annotations

import json
import os

from amnesia.api_objects.types import IngestionRunSummary
from amnesia.constants import STATUS_ERROR, STATUS_INGESTING, STATUS_NEVER_RUN
from amnesia.internal.events import InternalEvent
from amnesia.models import SourceStatus

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

ASCII_BANNER = r"""
  ▄▄▄▄                         ▄▄                                 ▀
 ▄▀  ▀▄ ▄▄▄▄    ▄▄▄   ▄ ▄▄     ██   ▄▄▄▄▄  ▄ ▄▄    ▄▄▄    ▄▄▄   ▄▄▄     ▄▄▄
 █    █ █▀ ▀█  █▀  █  █▀  █   █  █  █ █ █  █▀  █  █▀  █  █   ▀    █    ▀   █
 █    █ █   █  █▀▀▀▀  █   █   █▄▄█  █ █ █  █   █  █▀▀▀▀   ▀▀▀▄    █    ▄▀▀▀█
  █▄▄█  ██▄█▀  ▀█▄▄▀  █   █  █    █ █ █ █  █   █  ▀█▄▄▀  ▀▄▄▄▀  ▄▄█▄▄  ▀▄▄▀█
        █
        ▀
""".strip("\n")


def _status_style(status: str) -> str:
    if status == STATUS_ERROR:
        return "bold red"
    if status == STATUS_INGESTING:
        return "bold green"
    if status == STATUS_NEVER_RUN:
        return "yellow"
    return "dim"


def print_run_summary(summary: IngestionRunSummary) -> None:
    totals = summary.to_dict()["totals"]

    if not _HAS_RICH:
        print(
            "Ingestion complete:"
            f" records_seen={totals['records_seen']}"
            f" records_ingested={totals['records_ingested']}"
            f" records_filtered={totals['records_filtered']}"
            f" groups_seen={totals['groups_seen']}"
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
                f" filtered={src.records_filtered:<4} groups={src.groups_seen:<4}"
                f" events={src.inserted_events:<4} sessions={src.inserted_sessions:<4}"
                f" moments={src.inserted_moments:<4} skills={src.inserted_skills:<4}"
            )
            if src.error_message:
                msg += f" error={src.error_message}"
            print(msg)
        return

    console = Console()
    header = (
        f"records_seen={totals['records_seen']} | "
        f"records_ingested={totals['records_ingested']} | "
        f"records_filtered={totals['records_filtered']} | "
        f"groups_seen={totals['groups_seen']} | "
        f"events={totals['events']} | sessions={totals['sessions']} | "
        f"moments={totals['moments']} | skills={totals['skills']} | "
        f"duration={summary.duration_seconds:.2f}s"
    )
    console.print(Panel(header, title="Ingestion Complete", border_style="cyan"))

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Source", style="bold")
    table.add_column("Status")
    table.add_column("Seen", justify="right")
    table.add_column("Ingested", justify="right")
    table.add_column("Filtered", justify="right")
    table.add_column("Groups", justify="right")
    table.add_column("Events", justify="right")
    table.add_column("Sessions", justify="right")
    table.add_column("Moments", justify="right")
    table.add_column("Skills", justify="right")
    table.add_column("Error", overflow="fold")

    for src in summary.source_summaries:
        table.add_row(
            src.source,
            f"[{_status_style(src.status)}]{src.status}[/{_status_style(src.status)}]",
            str(src.records_seen),
            str(src.records_ingested),
            str(src.records_filtered),
            str(src.groups_seen),
            str(src.inserted_events),
            str(src.inserted_sessions),
            str(src.inserted_moments),
            str(src.inserted_skills),
            src.error_message or "",
        )
    console.print(table)


def print_run_summary_json(summary: IngestionRunSummary) -> None:
    print(json.dumps(summary.to_dict(), ensure_ascii=True))


def print_source_statuses(statuses: list[SourceStatus], configured: list[str]) -> None:
    known = {status.source for status in statuses}
    rows: list[tuple[str, str, int, str, str]] = []

    for status in statuses:
        rows.append(
            (
                status.source,
                status.status,
                status.records_ingested,
                status.last_poll_ts.isoformat(),
                status.error_message or "",
            )
        )

    for source in configured:
        if source not in known:
            rows.append((source, STATUS_NEVER_RUN, 0, "-", ""))

    if not _HAS_RICH:
        for source, status, ingested, last, error in sorted(rows, key=lambda item: item[0]):
            tail = f" error={error}" if error else ""
            print(f"{source:10} status={status:9} ingested={ingested:4} last={last}{tail}")
        return

    console = Console()
    table = Table(title="Source Status", show_header=True, header_style="bold cyan")
    table.add_column("Source", style="bold")
    table.add_column("Status")
    table.add_column("Ingested", justify="right")
    table.add_column("Last Poll")
    table.add_column("Error", overflow="fold")

    for source, status, ingested, last, error in sorted(rows, key=lambda item: item[0]):
        style = _status_style(status)
        table.add_row(
            source,
            f"[{style}]{status}[/{style}]",
            str(ingested),
            last,
            error,
        )
    console.print(table)


def print_banner() -> None:
    if os.getenv("AMNESIA_NO_BANNER", "").strip().lower() in {"1", "true", "yes"}:
        return
    if _HAS_RICH:
        console = Console()
        console.print("[bold cyan]" + ASCII_BANNER + "[/bold cyan]")
        return
    print(ASCII_BANNER)


def print_internal_events(events: list[InternalEvent]) -> None:
    if not events:
        return

    if not _HAS_RICH:
        for event in events:
            print(f"{event.ts.isoformat()} {event.topic} {event.payload}")
        return

    console = Console()
    table = Table(title="Recent Internal Events", show_header=True, header_style="bold cyan")
    table.add_column("Time")
    table.add_column("Topic")
    table.add_column("Payload", overflow="fold")
    for event in events:
        table.add_row(
            event.ts.isoformat(timespec="seconds"),
            event.topic,
            json.dumps(event.payload, ensure_ascii=True, sort_keys=True),
        )
    console.print(table)
