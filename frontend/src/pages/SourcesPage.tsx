import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SourceStatus, SourceDiagnostics } from "../lib/api";
import { cn, numberFormat, formatDateTime, sourceColor, sourceTextColor, timeAgo } from "../lib/utils";
import { EmptyState } from "../components/common/EmptyState";
import { SourceCard } from "../components/sources/SourceCard";
import { IconGrid, IconList, IconRefresh, IconActivity } from "../components/common/Icons";
import { useTableFilter, FilterInput, useResizableColumns } from "../lib/hooks";
import { useState, useCallback } from "react";

type LayoutMode = "compact" | "cards";

const COLS = [
  { key: "dot", initialWidth: 32, minWidth: 24 },
  { key: "source", initialWidth: 90, minWidth: 60 },
  { key: "status", initialWidth: 80, minWidth: 50 },
  { key: "heartbeat", initialWidth: 120, minWidth: 80 },
  { key: "seen", initialWidth: 80, minWidth: 50 },
  { key: "ingested", initialWidth: 80, minWidth: 50 },
  { key: "rate", initialWidth: 60, minWidth: 40 },
  { key: "progress", initialWidth: 0 },
  { key: "last_poll", initialWidth: 80, minWidth: 50 },
];

function HeartbeatLine({ data, source, width = 120, height = 20 }: { data: number[]; source: string; width?: number; height?: number }) {
  if (!data || data.length === 0) return null;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - (v / 100) * height}`).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block">
      <polyline
        points={pts}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={sourceTextColor(source)}
        style={{ filter: "drop-shadow(0 0 2px currentColor)" }}
      />
    </svg>
  );
}

function DiagnosticsPanel({ source, diag }: { source: string; diag: SourceDiagnostics }) {
  const diagColor = diag.diagnosis.status === "healthy" ? "text-ok" : diag.diagnosis.status === "degraded" ? "text-warn" : "text-err";
  const diagBg = diag.diagnosis.status === "healthy" ? "bg-ok-dim" : diag.diagnosis.status === "degraded" ? "bg-warn-dim" : "bg-err-dim";

  return (
    <div className="border-b border-line/30 bg-void-1/50 px-4 py-3 anim-fade-in">
      {/* Wide EEG chart */}
      <div className="mb-3 overflow-hidden rounded border border-line/20 bg-void-0 p-2">
        <div className="mb-1 font-sans text-[8px] font-semibold uppercase tracking-[0.15em] text-text-3">heartbeat — {source}</div>
        <HeartbeatLine data={diag.heartbeat} source={source} width={600} height={32} />
      </div>

      {/* 4-column grid */}
      <div className="grid grid-cols-4 gap-3">
        {/* Stats */}
        <div className="rounded border border-line/20 bg-void-0 p-2.5">
          <div className="mb-2 font-sans text-[8px] font-semibold uppercase tracking-[0.15em] text-text-3">stats</div>
          <div className="space-y-1">
            <DiagRow label="avg latency" value={`${diag.stats.avg_latency_ms}ms`} />
            <DiagRow label="p99 latency" value={`${diag.stats.p99_latency_ms}ms`} warn={diag.stats.p99_latency_ms > 500} />
            <DiagRow label="uptime" value={`${diag.stats.uptime_pct}%`} ok={diag.stats.uptime_pct > 99} />
            <DiagRow label="errors 24h" value={String(diag.stats.errors_24h)} warn={diag.stats.errors_24h > 5} />
            <DiagRow label="throughput" value={`${diag.stats.throughput_eps} e/s`} />
          </div>
        </div>

        {/* Info */}
        <div className="rounded border border-line/20 bg-void-0 p-2.5">
          <div className="mb-2 font-sans text-[8px] font-semibold uppercase tracking-[0.15em] text-text-3">info</div>
          <div className="space-y-1">
            <DiagRow label="version" value={diag.info.version} />
            <DiagRow label="protocol" value={diag.info.protocol} />
            <DiagRow label="adapter" value={diag.info.adapter} />
            <DiagRow label="pid" value={String(diag.info.pid)} />
          </div>
        </div>

        {/* Config */}
        <div className="rounded border border-line/20 bg-void-0 p-2.5">
          <div className="mb-2 font-sans text-[8px] font-semibold uppercase tracking-[0.15em] text-text-3">config</div>
          <div className="space-y-1">
            <DiagRow label="poll interval" value={`${diag.config.poll_interval_s}s`} />
            <DiagRow label="batch size" value={String(diag.config.batch_size)} />
            <DiagRow label="retry max" value={String(diag.config.retry_max)} />
            <DiagRow label="log path" value={diag.config.log_path} mono />
          </div>
        </div>

        {/* Diagnosis */}
        <div className="rounded border border-line/20 bg-void-0 p-2.5">
          <div className="mb-2 font-sans text-[8px] font-semibold uppercase tracking-[0.15em] text-text-3">diagnosis</div>
          <div className="mb-2 flex items-center gap-1.5">
            <span className={cn("inline-block h-2 w-2 rounded-full", diagBg)} />
            <span className={cn("text-[11px] font-semibold uppercase", diagColor)}>{diag.diagnosis.status}</span>
          </div>
          <div className="mb-1 font-mono text-[9px] tabular-nums text-text-3">checked {timeAgo(diag.diagnosis.last_check)}</div>
          {diag.diagnosis.issues.length > 0 && (
            <div className="mt-1.5 space-y-1">
              {diag.diagnosis.issues.map((issue, i) => (
                <div key={i} className="rounded bg-warn-dim px-2 py-0.5 font-mono text-[9px] text-warn">{issue}</div>
              ))}
            </div>
          )}
          {diag.diagnosis.issues.length === 0 && (
            <div className="font-mono text-[9px] text-ok">no issues detected</div>
          )}
        </div>
      </div>
    </div>
  );
}

function DiagRow({ label, value, ok, warn, mono }: { label: string; value: string; ok?: boolean; warn?: boolean; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="font-sans text-[9px] text-text-3">{label}</span>
      <span className={cn(
        "text-right font-mono text-[10px] tabular-nums",
        ok ? "text-ok" : warn ? "text-warn" : "text-text-1",
        mono && "text-[8px] break-all",
      )}>
        {value}
      </span>
    </div>
  );
}

export function SourcesPage() {
  const [layout, setLayout] = useState<LayoutMode>("compact");
  const [expandedSource, setExpandedSource] = useState<string | null>(null);

  const { data: sources, refetch, isFetching } = useQuery({
    queryKey: ["sources"],
    queryFn: api.sources,
  });

  const { data: audit } = useQuery({
    queryKey: ["audit"],
    queryFn: () => api.audit({ limit: 10 }),
  });

  const { data: diag } = useQuery({
    queryKey: ["sourceDiagnostics", expandedSource],
    queryFn: () => api.sourceDiagnostics(expandedSource!),
    enabled: !!expandedSource,
  });

  const { filteredItems, query, setQuery } = useTableFilter({
    items: sources?.items ?? [],
    searchFields: ["source", "status"],
  });

  const cols = useResizableColumns(COLS);

  const toggleExpand = useCallback((source: string) => {
    setExpandedSource((prev) => (prev === source ? null : source));
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Control bar */}
      <div className="flex shrink-0 items-center gap-3 border-b border-line/30 px-4 py-1.5">
        <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.1em] text-text-0">Sources</span>

        <FilterInput value={query} onChange={setQuery} placeholder="filter sources..." />

        <div className="toggle-group">
          <button className={layout === "compact" ? "active" : ""} onClick={() => setLayout("compact")}>
            <IconList size={11} className="mr-0.5 inline" />list
          </button>
          <button className={layout === "cards" ? "active" : ""} onClick={() => setLayout("cards")}>
            <IconGrid size={11} className="mr-0.5 inline" />grid
          </button>
        </div>

        <div className="ml-auto toggle-group">
          <button
            className={isFetching ? "active" : ""}
            onClick={() => void refetch()}
            disabled={isFetching}
          >
            <IconRefresh size={10} className={cn("mr-0.5 inline", isFetching && "animate-spin")} />
            {isFetching ? "syncing..." : "refresh"}
          </button>
        </div>
        <span className="font-mono text-[9px] tabular-nums text-text-3">{filteredItems.length} sources</span>
      </div>

      {/* Column headers (compact only) */}
      {layout === "compact" && (
        <div className="section-rule gap-0">
          {[
            { key: "dot", label: "" },
            { key: "source", label: "source" },
            { key: "status", label: "status" },
            { key: "heartbeat", label: "heartbeat" },
            { key: "seen", label: "seen", right: true },
            { key: "ingested", label: "ingested", right: true },
            { key: "rate", label: "rate", right: true },
            { key: "progress", label: "progress", flex: true },
            { key: "last_poll", label: "last poll", right: true },
          ].map((col) => (
            <span
              key={col.key}
              className={cn("relative shrink-0", col.flex && "min-w-0 flex-1", col.right && "text-right")}
              style={!col.flex && cols.widths[col.key] ? { width: cols.widths[col.key], flexShrink: 0 } : undefined}
            >
              {col.label}
              {!col.flex && col.label && <div {...cols.getResizeHandleProps(col.key)} />}
            </span>
          ))}
        </div>
      )}

      {/* Data */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {filteredItems.length > 0 ? (
          layout === "cards" ? (
            <div className="grid grid-cols-2 gap-3 p-4 xl:grid-cols-3">
              {filteredItems.map((src) => (
                <SourceCard key={src.source} source={src} onSelect={toggleExpand} expanded={expandedSource === src.source} diagnostics={expandedSource === src.source ? diag : null} />
              ))}
            </div>
          ) : (
            <div>
              {filteredItems.map((src) => (
                <SourceRow
                  key={src.source}
                  source={src}
                  widths={cols.widths}
                  expanded={expandedSource === src.source}
                  diagnostics={expandedSource === src.source ? diag : null}
                  onToggle={toggleExpand}
                />
              ))}

              {/* Error messages */}
              {filteredItems.filter((s) => s.error_message).map((src) => (
                <div key={`err-${src.source}`} className="flex items-center gap-2 border-b border-err-dim px-4 py-1.5 text-[10px]">
                  <span className="font-semibold uppercase text-err">{src.source}</span>
                  <span className="text-err/70">{src.error_message}</span>
                </div>
              ))}
            </div>
          )
        ) : (
          <EmptyState
            title="No sources"
            description="Configure sources in config.yaml and run the daemon."
          />
        )}

        {/* Audit log */}
        {audit && audit.items.length > 0 && (
          <div className="mt-2">
            <div className="section-rule gap-0">
              <span className="w-[160px] shrink-0">time</span>
              <span className="w-[100px] shrink-0">source</span>
              <span className="w-[80px] shrink-0 text-right">events</span>
              <span className="w-[80px] shrink-0 text-right">sessions</span>
              <span className="min-w-0 flex-1 text-right">moments</span>
            </div>
            {audit.items.map((row, i) => (
              <div key={i} className="data-row">
                <span className="w-[160px] shrink-0 tabular-nums text-text-2">
                  {formatDateTime(row.ts as string)}
                </span>
                <span className="flex w-[100px] shrink-0 items-center gap-1.5 font-medium text-text-1">
                  <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(row.source as string))} />
                  {row.source as string}
                </span>
                <span className="w-[80px] shrink-0 text-right tabular-nums text-text-1">
                  {numberFormat(row.event_count as number)}
                </span>
                <span className="w-[80px] shrink-0 text-right tabular-nums text-text-2">
                  {numberFormat(row.session_count as number)}
                </span>
                <span className="min-w-0 flex-1 text-right tabular-nums text-text-2">
                  {numberFormat(row.moment_count as number)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SourceRow({ source: src, widths, expanded, diagnostics, onToggle }: {
  source: SourceStatus;
  widths: Record<string, number>;
  expanded: boolean;
  diagnostics: SourceDiagnostics | null | undefined;
  onToggle: (source: string) => void;
}) {
  const pct = src.records_seen > 0 ? ((src.records_ingested / src.records_seen) * 100) : 0;
  const isIngesting = src.status === "ingesting";
  const isError = src.status === "error";

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={() => onToggle(src.source)}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onToggle(src.source); } }}
        className={cn("data-row cursor-pointer", expanded && "selected")}
      >
        {/* Source dot */}
        <span className="flex items-center justify-center"
          style={widths.dot ? { width: widths.dot, flexShrink: 0 } : { width: 32, flexShrink: 0 }}>
          <span className={cn("h-2 w-2 rounded-full", sourceColor(src.source), isIngesting && "anim-pulse")} />
        </span>

        {/* Name */}
        <span className="shrink-0 font-medium capitalize text-text-0"
          style={widths.source ? { width: widths.source, flexShrink: 0 } : { width: 90, flexShrink: 0 }}>
          {src.source}
        </span>

        {/* Status */}
        <span className={cn(
          "shrink-0 text-[10px] font-semibold uppercase",
          isError ? "text-err" : isIngesting ? "text-ok" : "text-text-3",
        )} style={widths.status ? { width: widths.status, flexShrink: 0 } : { width: 80, flexShrink: 0 }}>
          {isIngesting && <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-ok anim-pulse" />}
          {src.status}
        </span>

        {/* Heartbeat */}
        <span className="shrink-0 flex items-center"
          style={widths.heartbeat ? { width: widths.heartbeat, flexShrink: 0 } : { width: 120, flexShrink: 0 }}>
          {src.heartbeat ? (
            <HeartbeatLine data={src.heartbeat} source={src.source} width={widths.heartbeat ? widths.heartbeat - 8 : 112} height={16} />
          ) : (
            <IconActivity size={12} className="text-text-3" />
          )}
        </span>

        {/* Seen */}
        <span className="shrink-0 text-right tabular-nums text-text-1"
          style={widths.seen ? { width: widths.seen, flexShrink: 0 } : { width: 80, flexShrink: 0 }}>
          {numberFormat(src.records_seen)}
        </span>

        {/* Ingested */}
        <span className="shrink-0 text-right tabular-nums text-text-1"
          style={widths.ingested ? { width: widths.ingested, flexShrink: 0 } : { width: 80, flexShrink: 0 }}>
          {numberFormat(src.records_ingested)}
        </span>

        {/* Rate */}
        <span className="shrink-0 text-right tabular-nums text-ok"
          style={widths.rate ? { width: widths.rate, flexShrink: 0 } : { width: 60, flexShrink: 0 }}>
          {pct.toFixed(1)}%
        </span>

        {/* Progress bar */}
        <span className="min-w-0 flex-1 px-3">
          <span className="block h-[3px] overflow-hidden rounded-full bg-void-3">
            <span
              className={cn("block h-full rounded-full transition-all", sourceColor(src.source))}
              style={{ width: `${Math.min(pct, 100)}%`, opacity: 0.7 }}
            />
          </span>
        </span>

        {/* Last poll */}
        <span className="shrink-0 text-right text-[10px] tabular-nums text-text-3"
          style={widths.last_poll ? { width: widths.last_poll, flexShrink: 0 } : { width: 80, flexShrink: 0 }}>
          {timeAgo(src.last_poll_ts)}
        </span>
      </div>

      {/* Expanded diagnostics */}
      {expanded && diagnostics && (
        <DiagnosticsPanel source={src.source} diag={diagnostics} />
      )}
    </>
  );
}
