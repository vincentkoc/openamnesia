import { cn, numberFormat, sourceColor, timeAgo } from "../../lib/utils";
import type { SourceStatus } from "../../lib/api";
import { Badge } from "../common/Badge";

interface Props {
  source: SourceStatus;
}

export function SourceCard({ source }: Props) {
  const pct = source.records_seen > 0
    ? ((source.records_ingested / source.records_seen) * 100).toFixed(1)
    : "0.0";

  return (
    <div className="glow-border group rounded-lg border border-line bg-void-1 p-4 transition-colors hover:border-line-bright hover:bg-void-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={cn("h-2.5 w-2.5 rounded-full", sourceColor(source.source))} />
          <span className="text-[13px] font-semibold capitalize text-text-0">
            {source.source}
          </span>
        </div>
        <Badge
          variant={
            source.status === "error" ? "err"
              : source.status === "ingesting" ? "ok"
                : "default"
          }
        >
          {source.status === "ingesting" && (
            <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-ok anim-pulse" />
          )}
          {source.status}
        </Badge>
      </div>

      {/* Stats */}
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-md bg-void-2 px-2 py-1.5">
          <div className="text-[14px] font-bold tabular-nums text-text-0">
            {numberFormat(source.records_seen)}
          </div>
          <div className="text-[9px] uppercase tracking-wider text-text-3">seen</div>
        </div>
        <div className="rounded-md bg-void-2 px-2 py-1.5">
          <div className="text-[14px] font-bold tabular-nums text-text-0">
            {numberFormat(source.records_ingested)}
          </div>
          <div className="text-[9px] uppercase tracking-wider text-text-3">ingested</div>
        </div>
        <div className="rounded-md bg-void-2 px-2 py-1.5">
          <div className="text-[14px] font-bold tabular-nums text-ok">{pct}%</div>
          <div className="text-[9px] uppercase tracking-wider text-text-3">rate</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3">
        <div className="h-[3px] overflow-hidden rounded-full bg-void-3">
          <div
            className={cn("h-full rounded-full transition-all", sourceColor(source.source))}
            style={{ width: `${Math.min(parseFloat(pct), 100)}%`, opacity: 0.7 }}
          />
        </div>
      </div>

      {/* Meta */}
      <div className="mt-2 text-[10px] text-text-3">
        last poll: {timeAgo(source.last_poll_ts)}
      </div>

      {/* Error */}
      {source.error_message && (
        <div className="mt-2 rounded-md bg-err-dim px-2.5 py-1.5 text-[10px] text-err">
          {source.error_message}
        </div>
      )}
    </div>
  );
}
