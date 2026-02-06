import { cn, numberFormat, sourceColor, statusColor, timeAgo } from "../../lib/utils";
import type { SourceStatus } from "../../lib/api";
import { Badge } from "../common/Badge";
import { Activity, AlertCircle, CheckCircle, Pause } from "lucide-react";

interface SourceCardProps {
  source: SourceStatus;
}

const statusIcons: Record<string, React.ReactNode> = {
  idle: <Pause className="h-4 w-4" />,
  ingesting: <Activity className="h-4 w-4" />,
  error: <AlertCircle className="h-4 w-4" />,
};

export function SourceCard({ source }: SourceCardProps) {
  return (
    <div className="animate-fade-in rounded-xl border border-cream-300 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center", sourceColor(source.source), "bg-opacity-20")}>
            <div className={cn("h-3 w-3 rounded-full", sourceColor(source.source))} />
          </div>
          <div>
            <h3 className="text-[14px] font-semibold capitalize text-ink-400">
              {source.source}
            </h3>
            <span className="text-[11px] text-ink-50">
              Last poll: {timeAgo(source.last_poll_ts)}
            </span>
          </div>
        </div>
        <Badge
          variant={
            source.status === "error"
              ? "error"
              : source.status === "ingesting"
                ? "success"
                : "default"
          }
        >
          <span className={cn("mr-1", statusColor(source.status))}>
            {statusIcons[source.status] ?? <CheckCircle className="h-3.5 w-3.5" />}
          </span>
          {source.status}
        </Badge>
      </div>

      {/* Stats */}
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-cream-50 px-3 py-2">
          <div className="text-[11px] text-ink-50">Seen</div>
          <div className="text-[16px] font-semibold tabular-nums text-ink-400">
            {numberFormat(source.records_seen)}
          </div>
        </div>
        <div className="rounded-lg bg-cream-50 px-3 py-2">
          <div className="text-[11px] text-ink-50">Ingested</div>
          <div className="text-[16px] font-semibold tabular-nums text-ink-400">
            {numberFormat(source.records_ingested)}
          </div>
        </div>
      </div>

      {/* Error */}
      {source.error_message && (
        <div className="mt-3 rounded-lg bg-error-100 p-2.5 text-[12px] text-error-500">
          {source.error_message}
        </div>
      )}

      {/* Ingestion bar */}
      {source.records_seen > 0 && (
        <div className="mt-3">
          <div className="h-1.5 overflow-hidden rounded-full bg-cream-200">
            <div
              className={cn("h-full rounded-full transition-all", sourceColor(source.source))}
              style={{
                width: `${Math.min((source.records_ingested / source.records_seen) * 100, 100)}%`,
              }}
            />
          </div>
          <div className="mt-1 text-right text-[10px] tabular-nums text-cream-500">
            {((source.records_ingested / source.records_seen) * 100).toFixed(1)}% ingested
          </div>
        </div>
      )}
    </div>
  );
}
