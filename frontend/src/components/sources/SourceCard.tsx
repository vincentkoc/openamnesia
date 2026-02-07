import { cn, numberFormat, sourceColor, sourceTextColor, timeAgo } from "../../lib/utils";
import type { SourceStatus, SourceDiagnostics } from "../../lib/api";

interface Props {
  source: SourceStatus;
  onSelect?: (source: string) => void;
  expanded?: boolean;
  diagnostics?: SourceDiagnostics | null;
}

function HeartbeatLine({ data, source, width = 200, height = 24 }: { data: number[]; source: string; width?: number; height?: number }) {
  if (!data || data.length === 0) return null;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - (v / 100) * height}`).join(" ");
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="block">
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

export function SourceCard({ source, onSelect, expanded, diagnostics }: Props) {
  const pct = source.records_seen > 0
    ? ((source.records_ingested / source.records_seen) * 100).toFixed(1)
    : "0.0";

  const isIngesting = source.status === "ingesting";
  const isError = source.status === "error";
  const diag = diagnostics;
  const diagStatus = diag?.diagnosis.status;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(source.source)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect?.(source.source); } }}
      className={cn(
        "card cursor-pointer rounded-lg border border-line/40 bg-void-1/60 p-3",
        expanded && "border-accent bg-accent-dim",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={cn("h-2.5 w-2.5 rounded-full", sourceColor(source.source), isIngesting && "anim-pulse")} />
          <span className="font-mono text-[12px] font-medium capitalize text-text-0">
            {source.source}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {diagStatus && (
            <span className={cn(
              "inline-block h-1.5 w-1.5 rounded-full",
              diagStatus === "healthy" ? "bg-ok" : diagStatus === "degraded" ? "bg-warn" : "bg-err",
            )} />
          )}
          <span className={cn(
            "text-[9px] font-semibold uppercase",
            isError ? "text-err" : isIngesting ? "text-ok" : "text-text-3",
          )}>
            {source.status}
          </span>
        </div>
      </div>

      {/* Heartbeat */}
      {source.heartbeat && (
        <div className="mt-2 overflow-hidden rounded border border-line/20 bg-void-0 px-1 py-1">
          <HeartbeatLine data={source.heartbeat} source={source.source} width={200} height={20} />
        </div>
      )}

      {/* Stats */}
      <div className="mt-2 flex items-center gap-3 text-[10px]">
        <div className="stat-pip"><span className="stat-value">{numberFormat(source.records_seen)}</span><span className="stat-label">seen</span></div>
        <div className="stat-pip"><span className="stat-value">{numberFormat(source.records_ingested)}</span><span className="stat-label">ingested</span></div>
        <div className="stat-pip"><span className="stat-value text-ok">{pct}%</span><span className="stat-label">rate</span></div>
      </div>

      {/* Progress bar */}
      <div className="mt-2">
        <div className="h-[3px] overflow-hidden rounded-full bg-void-3">
          <div
            className={cn("h-full rounded-full transition-all", sourceColor(source.source))}
            style={{ width: `${Math.min(parseFloat(pct), 100)}%`, opacity: 0.7 }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="mt-2 flex items-center justify-between">
        <span className="font-mono text-[9px] tabular-nums text-text-3">poll {timeAgo(source.last_poll_ts)}</span>
        {diag && diag.diagnosis.issues.length > 0 && (
          <span className="rounded bg-warn-dim px-1.5 py-0.5 font-mono text-[8px] text-warn">
            {diag.diagnosis.issues.length} issue{diag.diagnosis.issues.length > 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Error */}
      {source.error_message && (
        <div className="mt-2 rounded bg-err-dim px-2 py-1 font-mono text-[9px] text-err">
          {source.error_message}
        </div>
      )}

      {/* Expanded diagnostics in card mode */}
      {expanded && diag && (
        <div className="mt-3 space-y-2 border-t border-line/20 pt-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <div className="mb-1 font-sans text-[8px] font-semibold uppercase tracking-[0.15em] text-text-3">stats</div>
              <div className="space-y-0.5 font-mono text-[9px]">
                <div className="flex justify-between"><span className="text-text-3">latency</span><span className="text-text-1">{diag.stats.avg_latency_ms}ms</span></div>
                <div className="flex justify-between"><span className="text-text-3">uptime</span><span className="text-ok">{diag.stats.uptime_pct}%</span></div>
                <div className="flex justify-between"><span className="text-text-3">throughput</span><span className="text-text-1">{diag.stats.throughput_eps} e/s</span></div>
              </div>
            </div>
            <div>
              <div className="mb-1 font-sans text-[8px] font-semibold uppercase tracking-[0.15em] text-text-3">info</div>
              <div className="space-y-0.5 font-mono text-[9px]">
                <div className="flex justify-between"><span className="text-text-3">version</span><span className="text-text-1">{diag.info.version}</span></div>
                <div className="flex justify-between"><span className="text-text-3">protocol</span><span className="text-text-1">{diag.info.protocol}</span></div>
                <div className="flex justify-between"><span className="text-text-3">adapter</span><span className="text-text-1 truncate ml-1">{diag.info.adapter}</span></div>
              </div>
            </div>
          </div>
          {diag.diagnosis.issues.length > 0 && (
            <div className="space-y-1">
              {diag.diagnosis.issues.map((issue, i) => (
                <div key={i} className="rounded bg-warn-dim px-2 py-0.5 font-mono text-[8px] text-warn">{issue}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
