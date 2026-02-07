#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

os.environ.setdefault("XDG_CACHE_HOME", str(Path(".cache").resolve()))
os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from amnesia import __version__
from amnesia.config import StoreConfig
from amnesia.pipeline.cluster_enrich import ClusterEnrichmentOptions, enrich_clusters
from amnesia.pipeline.clustering import cluster_embeddings
from amnesia.pipeline.embedding import HashEmbeddingProvider, embed_events
from amnesia.pipeline.memory_materialize import materialize_from_enrichments
from amnesia.filters import parse_iso_ts
from amnesia.sdk.imessage import (
    IMessageIngestConfig,
    dump_imessage_config,
    load_imessage_config,
    result_to_json,
    run_imessage_ingest,
)
from amnesia.store.factory import build_store
from amnesia.utils.display.terminal import print_banner
from amnesia.utils.logging import debug_event, get_logger, setup_logging

DEFAULT_E2E_CONFIG_PATH = Path(".amnesia_imessage_e2e.yaml")
DEFAULT_INGEST_CONFIG_PATH = Path(".amnesia_imessage_ingest.yaml")


@dataclass(slots=True)
class IMessageE2EConfig:
    ingest_config_path: str = str(DEFAULT_INGEST_CONFIG_PATH)
    discovery_since: str | None = None
    discovery_limit: int = 5000
    embedding_dims: int = 128
    use_llm: bool = False
    llm_model: str = "gpt-5-nano"
    llm_max_clusters: int = 12
    llm_max_tokens: int = 80
    llm_retries: int = 3
    llm_retry_min_seconds: float = 0.5
    llm_retry_max_seconds: float = 4.0
    llm_throttle_seconds: float = 0.0
    clean_run: bool = True
    require_llm_success: bool = True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-command iMessage E2E (ingest + discovery)")
    parser.add_argument("--config", default=str(DEFAULT_E2E_CONFIG_PATH))
    parser.add_argument("--init-config", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--reset-state", action="store_true")
    parser.add_argument("--clean-run", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--use-llm", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument(
        "--require-llm-success", action=argparse.BooleanOptionalAction, default=None
    )
    parser.add_argument("--llm-model")
    parser.add_argument("--llm-max-clusters", type=int)
    parser.add_argument("--llm-max-tokens", type=int)
    parser.add_argument("--llm-retries", type=int)
    parser.add_argument("--llm-retry-min-seconds", type=float)
    parser.add_argument("--llm-retry-max-seconds", type=float)
    parser.add_argument("--llm-throttle-seconds", type=float)
    parser.add_argument("--discovery-limit", type=int)
    parser.add_argument("--discovery-since")
    parser.add_argument("--show-debug-trace", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def _is_explicit_all(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"none", "all"}


def _normalize_since(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw or _is_explicit_all(raw):
        return None
    parsed = parse_iso_ts(raw)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="seconds")


def _default_since_last_week() -> str:
    return (datetime.now(UTC) - timedelta(days=7)).isoformat(timespec="seconds")


def _load_e2e_config(path: Path) -> IMessageE2EConfig:
    if not path.exists():
        return IMessageE2EConfig()
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    llm_model_raw = raw.get("llm_model")
    llm_model = str(llm_model_raw or "gpt-5-nano")
    if llm_model == "gpt-4o-mini":
        llm_model = "gpt-5-nano"
    return IMessageE2EConfig(
        ingest_config_path=str(raw.get("ingest_config_path", str(DEFAULT_INGEST_CONFIG_PATH))),
        discovery_since=raw.get("discovery_since"),
        discovery_limit=int(raw.get("discovery_limit", 5000)),
        embedding_dims=int(raw.get("embedding_dims", 128)),
        use_llm=bool(raw.get("use_llm", False)),
        llm_model=llm_model,
        llm_max_clusters=int(raw.get("llm_max_clusters", 12)),
        llm_max_tokens=int(raw.get("llm_max_tokens", 80)),
        llm_retries=int(raw.get("llm_retries", 3)),
        llm_retry_min_seconds=float(raw.get("llm_retry_min_seconds", 0.5)),
        llm_retry_max_seconds=float(raw.get("llm_retry_max_seconds", 4.0)),
        llm_throttle_seconds=float(raw.get("llm_throttle_seconds", 0.0)),
        clean_run=bool(raw.get("clean_run", True)),
        require_llm_success=bool(raw.get("require_llm_success", True)),
    )


def _dump_e2e_config(path: Path, cfg: IMessageE2EConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(asdict(cfg), fh, sort_keys=False)


def _sqlite_path_from_dsn(dsn: str) -> Path | None:
    if not dsn.startswith("sqlite:///"):
        return None
    return Path(dsn.removeprefix("sqlite:///"))


def _clean_run_state(ingest_cfg) -> dict[str, bool]:
    cleaned: dict[str, bool] = {"db": False, "state": False}
    db_path = _sqlite_path_from_dsn(ingest_cfg.store_dsn)
    if db_path is not None and db_path.exists():
        db_path.unlink()
        cleaned["db"] = True
    state_path = Path(ingest_cfg.state_path)
    if state_path.exists():
        state_path.unlink()
        cleaned["state"] = True
    return cleaned


def _print_tables(
    console: Console,
    payload: dict[str, Any],
    ingest_cfg_path: Path,
    *,
    completed: bool = True,
) -> None:
    ingest = payload["ingest"]
    discovery = payload["discovery"]

    status = "[bold cyan]E2E complete[/bold cyan]" if completed else "[bold red]E2E halted[/bold red]"
    console.print(
        f"{status} source=imessage "
        f"seen={ingest['seen']} ingested={ingest['ingested']} events={ingest['events']} "
        f"clusters={discovery['clusters']}"
    )
    console.print(
        f"[dim]ingest_config={ingest_cfg_path} state={ingest['state_path']} "
        f"store={ingest['store_dsn']}[/dim]"
    )

    created = Table(title="Created", show_header=True, header_style="bold cyan")
    created.add_column("Object")
    created.add_column("Inserted", justify="right")
    created.add_row("events", str(ingest["inserted_events"]))
    created.add_row("sessions", str(ingest["inserted_sessions"]))
    created.add_row("moments", str(ingest["inserted_moments"]))
    created.add_row("entity_mentions", str(ingest["inserted_mentions"]))
    created.add_row("entity_rollups", str(ingest["inserted_rollups"]))
    created.add_row("embeddings", str(discovery["inserted"]["embeddings"]))
    created.add_row("clusters", str(discovery["inserted"]["clusters"]))
    created.add_row("memberships", str(discovery["inserted"]["memberships"]))
    created.add_row("cluster_enrichments", str(discovery["inserted"]["enrichments"]))
    created.add_row("skills", str(discovery["inserted"].get("skills", 0)))
    created.add_row("facts_exported", str(discovery["inserted"].get("facts_exported", 0)))
    created.add_row("llm_attempted", str(discovery["llm_stats"]["attempted"]))
    created.add_row("llm_succeeded", str(discovery["llm_stats"]["succeeded"]))
    created.add_row("llm_fallback", str(discovery["llm_stats"]["fallback"]))
    console.print(created)

    clusters = Table(title="Top Clusters", show_header=True, header_style="bold cyan")
    clusters.add_column("Size", justify="right")
    clusters.add_column("Label")
    for item in discovery["top_clusters"][:10]:
        clusters.add_row(str(item["size"]), item["label"])
    console.print(clusters)


def _print_debug_trace(console: Console, debug_buffer: list[tuple[str, str, str]]) -> None:
    if not debug_buffer:
        return
    trace = Table(title="Debug Trace", show_header=True, header_style="bold magenta")
    trace.add_column("Time")
    trace.add_column("Event")
    trace.add_column("Detail", overflow="fold")
    for ts, event, detail in debug_buffer[-30:]:
        trace.add_row(ts, event, detail)
    console.print(trace)


def _print_run_header(
    console: Console,
    *,
    e2e_config_path: Path,
    ingest_config_path: Path,
    e2e_cfg: IMessageE2EConfig,
    cleaned: dict[str, bool],
) -> None:
    print_banner()
    console.print(f"[bold]OpenAmnesia[/bold] 🧠  [dim]v{__version__} · iMessage E2E[/dim]")
    console.print("[bold]Run[/bold] ingest + discovery pipeline for iMessage")
    console.print(
        f"[bold]task[/bold] config={e2e_config_path} ingest_config={ingest_config_path} "
        f"discovery_limit={e2e_cfg.discovery_limit} discovery_since={e2e_cfg.discovery_since or 'all'} "
        f"use_llm={e2e_cfg.use_llm}"
    )
    console.print(
        "[dim]"
        f"clean_run={e2e_cfg.clean_run} db_reset={cleaned['db']} state_reset={cleaned['state']} "
        f"require_llm_success={e2e_cfg.require_llm_success}"
        "[/dim]"
    )
    if e2e_cfg.use_llm:
        console.print(
            "[dim]"
            f"llm model={e2e_cfg.llm_model} max_clusters={e2e_cfg.llm_max_clusters} "
            f"retries={e2e_cfg.llm_retries} throttle_s={e2e_cfg.llm_throttle_seconds}"
            "[/dim]"
        )
    console.print(
        "[dim]stages: ingest -> load_events -> embed -> cluster -> enrich -> store -> summary[/dim]"
    )


def _clip(value: object, limit: int = 96) -> str:
    text = str(value)
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _classify_llm_error(error: str) -> tuple[str, str]:
    low = error.lower()
    if "finish_reason='length'" in low or "finish_reason=\"length\"" in low:
        return (
            "llm_token_budget_error",
            "Model hit token/output budget before returning content. Increase --llm-max-tokens (try 240-480).",
        )
    if "api key" in low or "authentication" in low or "unauthorized" in low:
        return (
            "llm_auth_error",
            "Check OPENAI_API_KEY (or provider key) and model access permissions.",
        )
    if "rate limit" in low or "429" in low:
        return (
            "llm_rate_limited",
            "Increase retry/backoff or throttle; reduce --llm-max-clusters for this run.",
        )
    if "connection" in low or "connecterror" in low or "timed out" in low:
        return (
            "llm_connection_error",
            "Provider/network is unreachable. Verify internet/VPN/proxy and OpenAI endpoint access.",
        )
    return (
        "llm_unknown_error",
        "Set AMNESIA_LITELLM_LOG_LEVEL=INFO (or DEBUG with AMNESIA_LITELLM_TRACE=true) for deeper diagnostics.",
    )


def main() -> int:
    args = _parse_args()
    setup_logging(level=None)
    console = Console()
    logger = get_logger("amnesia.imessage_e2e")
    debug_buffer: list[tuple[str, str, str]] = []
    live_debug_stream = False

    e2e_config_path = Path(args.config)
    if args.init_config or not e2e_config_path.exists():
        _dump_e2e_config(e2e_config_path, IMessageE2EConfig())
        ingest_cfg_path = DEFAULT_INGEST_CONFIG_PATH
        if not ingest_cfg_path.exists():
            dump_imessage_config(ingest_cfg_path, IMessageIngestConfig())
        if args.init_config:
            if args.json:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "initialized_e2e_config": str(e2e_config_path),
                            "initialized_ingest_config": str(ingest_cfg_path),
                        },
                        ensure_ascii=True,
                    )
                )
            else:
                console.print(f"Initialized config: {e2e_config_path}")
                console.print(f"Initialized ingest config: {ingest_cfg_path}")
            return 0

    e2e_cfg = _load_e2e_config(e2e_config_path)
    if args.use_llm is not None:
        e2e_cfg.use_llm = args.use_llm
    if args.clean_run is not None:
        e2e_cfg.clean_run = args.clean_run
    if args.require_llm_success is not None:
        e2e_cfg.require_llm_success = args.require_llm_success
    if args.llm_model:
        e2e_cfg.llm_model = args.llm_model
    if args.llm_max_clusters is not None:
        e2e_cfg.llm_max_clusters = args.llm_max_clusters
    if args.llm_max_tokens is not None:
        e2e_cfg.llm_max_tokens = args.llm_max_tokens
    if args.llm_retries is not None:
        e2e_cfg.llm_retries = args.llm_retries
    if args.llm_retry_min_seconds is not None:
        e2e_cfg.llm_retry_min_seconds = args.llm_retry_min_seconds
    if args.llm_retry_max_seconds is not None:
        e2e_cfg.llm_retry_max_seconds = args.llm_retry_max_seconds
    if args.llm_throttle_seconds is not None:
        e2e_cfg.llm_throttle_seconds = args.llm_throttle_seconds
    if args.discovery_limit is not None:
        e2e_cfg.discovery_limit = args.discovery_limit
    if args.discovery_since is not None:
        e2e_cfg.discovery_since = args.discovery_since

    explicit_all = _is_explicit_all(e2e_cfg.discovery_since)
    normalized_since = _normalize_since(e2e_cfg.discovery_since)
    if normalized_since is None and not explicit_all:
        normalized_since = _default_since_last_week()
    e2e_cfg.discovery_since = normalized_since

    ingest_config_path = Path(e2e_cfg.ingest_config_path)
    if not ingest_config_path.exists():
        dump_imessage_config(ingest_config_path, IMessageIngestConfig())
    ingest_cfg = load_imessage_config(ingest_config_path)
    if args.reset_state:
        ingest_cfg.reset_state = True
    if e2e_cfg.clean_run:
        cleaned = _clean_run_state(ingest_cfg)
        ingest_cfg.reset_state = True
    else:
        cleaned = {"db": False, "state": False}

    if not args.json:
        _print_run_header(
            console,
            e2e_config_path=e2e_config_path,
            ingest_config_path=ingest_config_path,
            e2e_cfg=e2e_cfg,
            cleaned=cleaned,
        )

    progress: Progress | None = None
    stage_task_id: int | None = None
    base_steps = 5  # ingest, load_events, embed, cluster, store_write
    if not args.json:
        progress = Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        )
        progress.start()
        stage_task_id = progress.add_task("ingest", total=base_steps)
        live_debug_stream = logger.isEnabledFor(10)

    def emit_debug(event: str, **fields: object) -> None:
        if not logger.isEnabledFor(10):  # DEBUG
            return
        progress_active = progress is not None and not args.json
        ts = datetime.now().strftime("%H:%M:%S")
        if progress_active:
            pairs = []
            for key, value in fields.items():
                if value is None:
                    continue
                pairs.append(f"{key}={_clip(value)}")
            detail = " ".join(pairs) if pairs else "-"
            progress.console.print(f"[dim]{ts} DEBUG[/dim] event={event} {detail}")
            debug_buffer.append(
                (
                    ts,
                    event,
                    detail,
                )
            )
            return
        debug_event(logger, event, **fields)

    emit_debug(
        "e2e_start",
        config=str(e2e_config_path),
        ingest_config=str(ingest_config_path),
        use_llm=e2e_cfg.use_llm,
        llm_model=e2e_cfg.llm_model if e2e_cfg.use_llm else None,
        llm_retries=e2e_cfg.llm_retries if e2e_cfg.use_llm else None,
        llm_throttle_seconds=e2e_cfg.llm_throttle_seconds if e2e_cfg.use_llm else None,
        discovery_limit=e2e_cfg.discovery_limit,
        clean_run=e2e_cfg.clean_run,
        cleaned_db=cleaned["db"],
        cleaned_state=cleaned["state"],
    )
    emit_debug(
        "hook.pipeline_sequence",
        stages="ingest,load_events,embed,cluster,enrich,store,summary",
    )

    emit_debug("hook.ingest.start", source="imessage")
    ingest_result = run_imessage_ingest(ingest_cfg)
    if progress is not None and stage_task_id is not None:
        progress.update(stage_task_id, description="ingest")
        progress.advance(stage_task_id, 1)
    emit_debug(
        "hook.ingest.completed",
        seen=ingest_result.seen,
        ingested=ingest_result.ingested,
        filtered=ingest_result.filtered,
        events=ingest_result.events,
    )
    if ingest_result.error is not None:
        if progress is not None:
            progress.stop()
        if args.json:
            print(result_to_json(ingest_result))
        else:
            console.print(
                Panel(
                    "[bold]Ingestion failed[/bold]\n"
                    f"{ingest_result.error}\n\n"
                    f"[dim]{ingest_result.hint or '-'}[/dim]\n"
                    f"[dim]Requested settings open: {ingest_result.disk_access_request_attempted} "
                    f"(opened={ingest_result.disk_access_settings_opened})[/dim]",
                    title="Source Error: imessage",
                    border_style="red",
                )
            )
            if args.show_debug_trace or not live_debug_stream:
                _print_debug_trace(console, debug_buffer)
        return 2

    emit_debug("hook.discovery.load_events.start", source="imessage")
    store = build_store(StoreConfig(backend="sqlite", dsn=ingest_cfg.store_dsn))
    store.init_schema()
    events = store.list_events_for_source(
        source="imessage",
        since_ts=e2e_cfg.discovery_since,
        limit=e2e_cfg.discovery_limit,
    )
    events.sort(key=lambda item: item.ts)
    if progress is not None and stage_task_id is not None:
        progress.update(stage_task_id, description="load events")
        progress.advance(stage_task_id, 1)
    emit_debug("hook.discovery.load_events.completed", events=len(events))
    events_by_id = {event.event_id: event for event in events}
    emit_debug("hook.discovery.embed.start", dims=max(16, e2e_cfg.embedding_dims), events=len(events))
    embedding_result = embed_events(
        events,
        provider=HashEmbeddingProvider(dimensions=max(16, e2e_cfg.embedding_dims)),
    )
    if progress is not None and stage_task_id is not None:
        progress.update(stage_task_id, description="embed")
        progress.advance(stage_task_id, 1)
    emit_debug("hook.discovery.embed.completed", embeddings=len(embedding_result.embeddings))
    emit_debug("hook.discovery.cluster.start", embeddings=len(embedding_result.embeddings))
    cluster_result = cluster_embeddings(events_by_id, embedding_result.embeddings)
    if progress is not None and stage_task_id is not None:
        progress.update(stage_task_id, description="cluster")
        progress.advance(stage_task_id, 1)
    emit_debug("hook.discovery.cluster.completed", clusters=len(cluster_result.clusters))

    llm_stats = {"attempted": 0, "succeeded": 0, "fallback": 0}
    llm_target = 0
    if e2e_cfg.use_llm:
        llm_target = min(max(1, e2e_cfg.llm_max_clusters), len(cluster_result.clusters))
    if progress is not None and stage_task_id is not None and llm_target > 0:
        progress.update(
            stage_task_id,
            total=base_steps + llm_target,
            description=f"llm 0/{llm_target}",
        )
    emit_debug(
        "hook.discovery.enrich.start",
        use_llm=e2e_cfg.use_llm,
        llm_model=e2e_cfg.llm_model if e2e_cfg.use_llm else None,
        llm_target=llm_target,
        llm_retries=e2e_cfg.llm_retries if e2e_cfg.use_llm else None,
        llm_retry_min_seconds=e2e_cfg.llm_retry_min_seconds if e2e_cfg.use_llm else None,
        llm_retry_max_seconds=e2e_cfg.llm_retry_max_seconds if e2e_cfg.use_llm else None,
        llm_throttle_seconds=e2e_cfg.llm_throttle_seconds if e2e_cfg.use_llm else None,
    )

    def _on_enrich_progress(item: dict[str, object]) -> None:
        attempted = bool(item.get("llm_attempted"))
        succeeded = bool(item.get("llm_succeeded"))
        error = item.get("llm_error")
        if attempted:
            llm_stats["attempted"] += 1
            if succeeded:
                llm_stats["succeeded"] += 1
            else:
                llm_stats["fallback"] += 1
        if progress is not None and stage_task_id is not None and llm_target > 0:
            progress.advance(stage_task_id, 1)
            progress.update(
                stage_task_id,
                description=f"llm {min(llm_stats['attempted'], llm_target)}/{llm_target}",
            )
        emit_debug(
            "cluster_enrich_progress",
            cluster_id=item.get("cluster_id"),
            size=item.get("size"),
            provider=item.get("provider"),
            llm_attempted=attempted,
            llm_succeeded=succeeded,
            llm_error=error,
        )

    try:
        enrichments = enrich_clusters(
            cluster_result.clusters,
            cluster_result.memberships,
            events_by_id,
            options=ClusterEnrichmentOptions(
                use_llm=e2e_cfg.use_llm,
                model=e2e_cfg.llm_model,
                max_clusters=max(1, e2e_cfg.llm_max_clusters),
                max_tokens=max(32, e2e_cfg.llm_max_tokens),
                llm_retries=max(1, e2e_cfg.llm_retries),
                llm_retry_min_seconds=max(0.05, e2e_cfg.llm_retry_min_seconds),
                llm_retry_max_seconds=max(0.05, e2e_cfg.llm_retry_max_seconds),
                llm_throttle_seconds=max(0.0, e2e_cfg.llm_throttle_seconds),
                fail_fast_on_llm_error=e2e_cfg.use_llm and e2e_cfg.require_llm_success,
                on_progress=_on_enrich_progress,
            ),
        )
    except Exception as exc:
        if progress is not None:
            progress.stop()
        err_text = str(exc)
        err_code, err_hint = _classify_llm_error(err_text)
        emit_debug("e2e_failed", reason="llm_fail_fast", error=err_text, error_code=err_code)
        if args.json:
            print(
                json.dumps(
                    {
                        "error": "LLM enrichment failed in strict mode.",
                        "detail": err_text,
                        "error_code": err_code,
                        "hint": err_hint,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
        else:
            console.print(
                Panel(
                    "[bold]LLM enrichment failed[/bold]\n"
                    f"{err_text}\n\n"
                    f"[bold]Error code:[/bold] {err_code}\n"
                    f"[dim]{err_hint}[/dim]\n\n"
                    "[dim]Strict mode stopped immediately on first failed cluster enrichment.[/dim]",
                    title="E2E Error",
                    border_style="red",
                )
            )
            if args.show_debug_trace or not live_debug_stream:
                _print_debug_trace(console, debug_buffer)
        return 3
    emit_debug(
        "hook.discovery.enrich.completed",
        enrichments=len(enrichments),
        llm_attempted=llm_stats["attempted"],
        llm_succeeded=llm_stats["succeeded"],
        llm_fallback=llm_stats["fallback"],
    )
    emit_debug("hook.discovery.store.start")
    inserted_embeddings = store.save_event_embeddings(embedding_result.embeddings)
    inserted_clusters = store.save_event_clusters(cluster_result.clusters)
    inserted_memberships = store.save_cluster_memberships(cluster_result.memberships)
    inserted_enrichments = store.save_cluster_enrichments(enrichments)
    memory_result = materialize_from_enrichments(cluster_result.clusters, enrichments)
    inserted_skills = store.save_skill_candidates(memory_result.skill_candidates)
    facts_export_path = Path("./exports/imessage_fact_candidates.json")
    facts_export_path.parent.mkdir(parents=True, exist_ok=True)
    facts_export_path.write_text(
        json.dumps(memory_result.fact_candidates, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    store.close()
    if progress is not None and stage_task_id is not None:
        progress.update(stage_task_id, description="store")
        progress.advance(stage_task_id, 1)
        progress.stop()
    emit_debug(
        "hook.discovery.store.completed",
        embeddings=inserted_embeddings,
        clusters=inserted_clusters,
        memberships=inserted_memberships,
        enrichments=inserted_enrichments,
        skills=inserted_skills,
        facts_exported=len(memory_result.fact_candidates),
        facts_export_path=str(facts_export_path),
    )

    payload = {
        "ingest": ingest_result.to_dict(),
        "discovery": {
            "events": len(events),
            "embeddings": len(embedding_result.embeddings),
            "clusters": len(cluster_result.clusters),
            "memberships": len(cluster_result.memberships),
            "enrichments": len(enrichments),
            "inserted": {
                "embeddings": inserted_embeddings,
                "clusters": inserted_clusters,
                "memberships": inserted_memberships,
                "enrichments": inserted_enrichments,
                "skills": inserted_skills,
                "facts_exported": len(memory_result.fact_candidates),
            },
            "top_clusters": [
                {
                    "cluster_id": cluster.cluster_id,
                    "label": cluster.label,
                    "size": cluster.size,
                }
                for cluster in cluster_result.clusters[:10]
            ],
            "embedding_backend": "hash-embed-v1",
            "clustering_algorithm": "prefix-bucket-v1",
            "llm_enrichment": e2e_cfg.use_llm,
            "llm_model": e2e_cfg.llm_model if e2e_cfg.use_llm else None,
            "llm_max_clusters": e2e_cfg.llm_max_clusters if e2e_cfg.use_llm else None,
            "llm_max_tokens": e2e_cfg.llm_max_tokens if e2e_cfg.use_llm else None,
            "llm_stats": llm_stats,
            "clean_run": {
                "enabled": e2e_cfg.clean_run,
                "db_reset": cleaned["db"],
                "state_reset": cleaned["state"],
            },
            "facts_export_path": str(facts_export_path),
        },
    }
    emit_debug(
        "e2e_completed",
        events=payload["discovery"]["events"],
        clusters=payload["discovery"]["clusters"],
        llm_attempted=llm_stats["attempted"],
        llm_succeeded=llm_stats["succeeded"],
        llm_fallback=llm_stats["fallback"],
    )

    if e2e_cfg.use_llm and e2e_cfg.require_llm_success and llm_stats["succeeded"] == 0:
        emit_debug(
            "e2e_failed",
            reason="llm_required_no_success",
            llm_attempted=llm_stats["attempted"],
            llm_succeeded=llm_stats["succeeded"],
            llm_fallback=llm_stats["fallback"],
        )
        if args.json:
            payload["error"] = (
                "LLM enrichment required success but no cluster-level LLM calls succeeded."
            )
            print(json.dumps(payload, ensure_ascii=True, indent=2))
        else:
            console.print(
                Panel(
                    "[bold]LLM enrichment failed[/bold]\n"
                    "No cluster-level LLM enrichments succeeded.\n\n"
                    "[dim]Use --no-require-llm-success to allow fallback mode, "
                    "or fix provider/network credentials.[/dim]",
                    title="E2E Error",
                    border_style="red",
                )
            )
            _print_tables(console, payload, ingest_config_path, completed=False)
            if args.show_debug_trace or not live_debug_stream:
                _print_debug_trace(console, debug_buffer)
        return 3

    if args.json:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0

    _print_tables(console, payload, ingest_config_path)
    if args.show_debug_trace or not live_debug_stream:
        _print_debug_trace(console, debug_buffer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
