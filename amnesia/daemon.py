from __future__ import annotations

import argparse
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml

from amnesia.api_objects.types import IngestionRunSummary, SourceIngestionSummary
from amnesia.config import AppConfig, dump_default_config, load_config
from amnesia.connectors.registry import build_connectors
from amnesia.constants import STATUS_ERROR, STATUS_IDLE, STATUS_INGESTING, STATUS_NEVER_RUN
from amnesia.exports.md_daily import export_daily_moments
from amnesia.exports.skill_yaml import export_skills_yaml
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
from amnesia.utils.display.terminal import print_run_summary, print_run_summary_json
from amnesia.utils.logging import debug_event, get_logger, setup_logging


@dataclass(slots=True)
class RuntimeState:
    per_source: dict

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


class Daemon:
    def __init__(self, config: AppConfig):
        self.config = config
        self.connectors = build_connectors(config.sources)
        self.store = build_store(config.store)
        self.state_path = Path(config.daemon.state_path)
        self.state = load_state(self.state_path)
        self.hooks = HookRegistry()
        load_plugins(config.hooks.plugins, self.hooks)
        self.running = True
        self.logger = get_logger("amnesia.daemon")

    def stop(self, *_args: object) -> None:
        self.running = False

    def run(self, once: bool = False) -> IngestionRunSummary:
        self.store.init_schema()
        started = utc_now()
        cycle_summary: list[SourceIngestionSummary] = []

        self.logger.info(
            "Starting ingestion run (once=%s, sources=%s)",
            once,
            [connector.source_name for connector in self.connectors],
        )

        while self.running:
            total_records = 0
            cycle_summary = []

            for connector in self.connectors:
                source_name = connector.source_name
                source_state = self.state.per_source.get(source_name, {})
                now = utc_now()

                try:
                    poll_result = connector.poll(source_state)
                    records = poll_result.records
                    self.state.per_source[source_name] = poll_result.state
                    total_records += len(records)

                    if records:
                        counts = self._process_records(source_name, records)
                        status = STATUS_INGESTING
                    else:
                        counts = ProcessCounts(0, 0, 0, 0)
                        status = STATUS_IDLE

                    summary = SourceIngestionSummary(
                        source=source_name,
                        status=status,
                        records_seen=len(records),
                        records_ingested=len(records),
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
                            records_seen=len(records),
                            records_ingested=len(records),
                            error_message=None,
                        )
                    )
                    debug_event(
                        self.logger,
                        "source_polled",
                        source=source_name,
                        status=status,
                        records=len(records),
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
                self.logger.info("Processed %s records across sources", total_records)

        self.store.close()
        ended = utc_now()
        summary = IngestionRunSummary(
            started_at=started,
            ended_at=ended,
            once=once,
            source_summaries=cycle_summary,
        )
        self.logger.info(
            "Ingestion finished: records_seen=%s events=%s sessions=%s moments=%s skills=%s",
            summary.total_records_seen,
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
        known = {status.source for status in statuses}

        for status in statuses:
            print(
                f"{status.source:10} status={status.status:9} ingested={status.records_ingested:4}"
                f" last={status.last_poll_ts.isoformat()}"
            )

        for source in configured:
            if source not in known:
                print(f"{source:10} status={STATUS_NEVER_RUN}")

        self.store.close()

    def _process_records(self, source_name: str, records: list) -> ProcessCounts:
        ctx = PipelineContext()
        ctx.derived["records"] = records

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

        return ProcessCounts(
            inserted_events=inserted_events,
            inserted_sessions=inserted_sessions,
            inserted_moments=inserted_moments,
            inserted_skills=inserted_skills,
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Amnesia local ingestion daemon")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config")
    parser.add_argument("--init-config", action="store_true", help="Write default config and exit")
    parser.add_argument("--once", action="store_true", help="Run one ingestion pass and exit")
    parser.add_argument("--sources", action="store_true", help="Print source statuses and exit")
    parser.add_argument("--log-level", help="Override log level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--json-summary", action="store_true", help="Print run summary as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.init_config:
        dump_default_config(args.config)
        print(f"Wrote default config to {args.config}")
        return 0

    config = load_config(args.config)
    setup_logging(level=args.log_level or config.logging.level)
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
