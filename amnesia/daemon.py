from __future__ import annotations

import argparse
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from amnesia.api_objects.types import IngestionRunSummary, SourceIngestionSummary
from amnesia.config import AppConfig, SourceConfig, dump_default_config, load_config
from amnesia.connectors.base import SourceRecord
from amnesia.connectors.registry import build_connectors
from amnesia.constants import STATUS_ERROR, STATUS_IDLE, STATUS_INGESTING
from amnesia.exports.md_daily import export_daily_moments
from amnesia.exports.skill_yaml import export_skills_yaml
from amnesia.filters import (
    SourceFilterPipeline,
    make_exclude_contains_filter,
    make_include_contains_filter,
)
from amnesia.internal.events import EventBus, InternalEvent
from amnesia.models import IngestAudit, SourceStatus, utc_now
from amnesia.pipeline.base import PipelineContext
from amnesia.pipeline.extract import annotate_moments
from amnesia.pipeline.hooks import HookRegistry
from amnesia.pipeline.momentize import momentize_sessions
from amnesia.pipeline.normalize import normalize_records
from amnesia.pipeline.optimize import optimize_skill
from amnesia.pipeline.plugin_loader import load_plugins
from amnesia.pipeline.sessionize import sessionize_events
from amnesia.pipeline.skill_mine import mine_skill_candidates
from amnesia.store.factory import build_store
from amnesia.utils.display.terminal import (
    print_banner,
    print_internal_events,
    print_run_summary,
    print_run_summary_json,
    print_source_statuses,
)
from amnesia.utils.logging import debug_event, get_logger, setup_logging


@dataclass(slots=True)
class RuntimeState:
    per_source: dict[str, dict[str, Any]]

    @staticmethod
    def empty() -> RuntimeState:
        return RuntimeState(per_source={})


@dataclass(slots=True)
class ProcessCounts:
    inserted_events: int
    inserted_sessions: int
    inserted_moments: int
    inserted_skills: int


def load_state(path: Path) -> RuntimeState:
    if not path.exists():
        return RuntimeState.empty()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return RuntimeState(per_source=raw.get("per_source", {}))


def save_state(path: Path, state: RuntimeState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"per_source": state.per_source}
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=True)


def build_source_filter_pipeline(source: SourceConfig) -> SourceFilterPipeline:
    pipeline = SourceFilterPipeline()
    if source.include_contains:
        pipeline.add(make_include_contains_filter(source.include_contains))
    if source.exclude_contains:
        pipeline.add(make_exclude_contains_filter(source.exclude_contains))
    return pipeline


class Daemon:
    def __init__(self, config: AppConfig):
        self.config = config
        self.connectors = build_connectors(config.sources)
        self.source_configs = {source.name: source for source in config.sources}
        self.source_filters = {
            source.name: build_source_filter_pipeline(source) for source in config.sources
        }

        self.store = build_store(config.store)
        self.state_path = Path(config.daemon.state_path)
        self.state = load_state(self.state_path)
        self.hooks = HookRegistry()
        load_plugins(config.hooks.plugins, self.hooks)

        self.event_bus = EventBus()
        self.running = True
        self.logger = get_logger("amnesia.daemon")

    def stop(self, *_args: object) -> None:
        self.running = False
        self.event_bus.emit("run.stop_requested")

    def run(self, once: bool = False) -> IngestionRunSummary:
        self.store.init_schema()
        started = utc_now()
        cycle_summary: list[SourceIngestionSummary] = []

        source_names = [connector.source_name for connector in self.connectors]
        self.event_bus.emit("run.started", once=once, sources=source_names)
        self.logger.info("Starting ingestion run (once=%s, sources=%s)", once, source_names)

        while self.running:
            total_records = 0
            cycle_summary = []

            for connector in self.connectors:
                source_name = connector.source_name
                source_state = self.state.per_source.get(source_name, {})
                now = utc_now()
                self.event_bus.emit("source.poll.started", source=source_name)

                try:
                    poll_result = connector.poll(source_state)
                    records = poll_result.records
                    self.state.per_source[source_name] = poll_result.state
                    seen = poll_result.stats.items_seen
                    groups = poll_result.stats.groups_seen
                    group_counts = poll_result.stats.item_counts_by_group

                    filter_pipeline = self.source_filters.get(source_name, SourceFilterPipeline())
                    filtered_records, dropped_count = filter_pipeline.apply(records)
                    ingested = len(filtered_records)
                    total_records += ingested

                    self.event_bus.emit(
                        "source.poll.completed",
                        source=source_name,
                        items_seen=seen,
                        items_ingested=ingested,
                        items_filtered=dropped_count,
                        groups_seen=groups,
                    )

                    if filtered_records:
                        counts = self._process_records(source_name, filtered_records)
                        status = STATUS_INGESTING
                    else:
                        counts = ProcessCounts(0, 0, 0, 0)
                        status = STATUS_IDLE

                    summary = SourceIngestionSummary(
                        source=source_name,
                        status=status,
                        records_seen=seen,
                        records_ingested=ingested,
                        records_filtered=dropped_count,
                        groups_seen=groups,
                        group_item_counts=group_counts,
                        inserted_events=counts.inserted_events,
                        inserted_sessions=counts.inserted_sessions,
                        inserted_moments=counts.inserted_moments,
                        inserted_skills=counts.inserted_skills,
                    )
                    cycle_summary.append(summary)

                    self.store.save_source_status(
                        SourceStatus(
                            source=source_name,
                            status=status,
                            last_poll_ts=now,
                            records_seen=seen,
                            records_ingested=ingested,
                            error_message=None,
                        )
                    )
                    debug_event(
                        self.logger,
                        "source_polled",
                        source=source_name,
                        status=status,
                        items_seen=seen,
                        items_ingested=ingested,
                        items_filtered=dropped_count,
                        groups_seen=groups,
                        inserted_events=counts.inserted_events,
                    )
                except Exception as exc:
                    cycle_summary.append(
                        SourceIngestionSummary(
                            source=source_name,
                            status=STATUS_ERROR,
                            records_seen=0,
                            records_ingested=0,
                            error_message=str(exc),
                        )
                    )
                    self.store.save_source_status(
                        SourceStatus(
                            source=source_name,
                            status=STATUS_ERROR,
                            last_poll_ts=now,
                            records_seen=0,
                            records_ingested=0,
                            error_message=str(exc),
                        )
                    )
                    self.event_bus.emit("source.poll.error", source=source_name, error=str(exc))
                    self.logger.exception("Connector failure for source=%s", source_name)

            save_state(self.state_path, self.state)

            if once:
                break

            if total_records == 0:
                self.logger.debug(
                    "No new records. Sleeping for %ss", self.config.daemon.poll_interval_seconds
                )
                time.sleep(self.config.daemon.poll_interval_seconds)
            else:
                self.logger.info("Processed %s ingested records across sources", total_records)

        self.store.close()
        ended = utc_now()
        summary = IngestionRunSummary(
            started_at=started,
            ended_at=ended,
            once=once,
            source_summaries=cycle_summary,
        )
        self.event_bus.emit("run.completed", summary=summary.to_dict())
        self.logger.info(
            (
                "Ingestion finished: seen=%s ingested=%s filtered=%s groups=%s "
                "events=%s sessions=%s moments=%s skills=%s"
            ),
            summary.total_records_seen,
            summary.total_records_ingested,
            summary.total_records_filtered,
            summary.total_groups_seen,
            summary.total_events,
            summary.total_sessions,
            summary.total_moments,
            summary.total_skills,
        )
        return summary

    def print_source_status(self) -> None:
        self.store.init_schema()
        statuses = self.store.list_source_status()
        configured = [src.name for src in self.config.sources if src.enabled]
        print_source_statuses(statuses, configured)
        self.store.close()

    def _process_records(self, source_name: str, records: list[SourceRecord]) -> ProcessCounts:
        ctx = PipelineContext()
        ctx.derived["records"] = records

        self.event_bus.emit("pipeline.normalize.start", source=source_name, count=len(records))
        ctx = self.hooks.run(self.hooks.pre_normalize, ctx)
        ctx.events = normalize_records(records)
        ctx = self.hooks.run(self.hooks.post_normalize, ctx)

        ctx.sessions = sessionize_events(ctx.events)
        ctx = self.hooks.run(self.hooks.post_sessionize, ctx)

        ctx.moments = momentize_sessions(ctx.sessions)
        ctx = self.hooks.run(self.hooks.post_momentize, ctx)

        ctx.moments = annotate_moments(ctx.moments, ctx.events)
        ctx = self.hooks.run(self.hooks.post_extract, ctx)

        candidates = mine_skill_candidates(ctx.moments)
        optimized = [optimize_skill(skill) for skill in candidates]
        ctx.derived["skills"] = optimized
        ctx = self.hooks.run(self.hooks.post_skill_mine, ctx)

        inserted_events = self.store.save_events(ctx.events)
        inserted_sessions = self.store.save_sessions(ctx.sessions)
        inserted_moments = self.store.save_moments(ctx.moments)
        inserted_skills = self.store.save_skill_candidates(ctx.derived["skills"])

        if self.config.exports.enabled:
            export_daily_moments(ctx.moments, out_dir=self.config.exports.daily_dir)
            export_skills_yaml(ctx.derived["skills"], out_dir=self.config.exports.skills_dir)

        self.store.append_ingest_audit(
            IngestAudit(
                audit_id=str(uuid.uuid4()),
                ts=utc_now(),
                source=source_name,
                event_count=inserted_events,
                session_count=inserted_sessions,
                moment_count=inserted_moments,
                skill_count=inserted_skills,
                details_json={"records": len(records)},
            )
        )

        self.event_bus.emit(
            "pipeline.completed",
            source=source_name,
            inserted_events=inserted_events,
            inserted_sessions=inserted_sessions,
            inserted_moments=inserted_moments,
            inserted_skills=inserted_skills,
        )

        return ProcessCounts(
            inserted_events=inserted_events,
            inserted_sessions=inserted_sessions,
            inserted_moments=inserted_moments,
            inserted_skills=inserted_skills,
        )

    def recent_events(self, limit: int = 100) -> list[InternalEvent]:
        return self.event_bus.recent(limit)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Amnesia local ingestion daemon")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config")
    parser.add_argument("--init-config", action="store_true", help="Write default config and exit")
    parser.add_argument("--once", action="store_true", help="Run one ingestion pass and exit")
    parser.add_argument("--sources", action="store_true", help="Print source statuses and exit")
    parser.add_argument("--log-level", help="Override log level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--json-summary", action="store_true", help="Print run summary as JSON")
    parser.add_argument("--events-limit", type=int, default=0, help="Print recent internal events")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.init_config:
        dump_default_config(args.config)
        print(f"Wrote default config to {args.config}")
        return 0

    config = load_config(args.config)
    setup_logging(level=args.log_level or config.logging.level)
    if not args.json_summary:
        print_banner()
    daemon = Daemon(config)

    if args.sources:
        daemon.print_source_status()
        return 0

    signal.signal(signal.SIGINT, daemon.stop)
    signal.signal(signal.SIGTERM, daemon.stop)

    summary = daemon.run(once=args.once)

    if args.once:
        if args.json_summary:
            print_run_summary_json(summary)
        else:
            print_run_summary(summary)
        if args.events_limit > 0:
            print_internal_events(daemon.recent_events(args.events_limit))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
