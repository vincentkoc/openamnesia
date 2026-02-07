import type { Event } from "../../lib/api";
import { cn, formatTime, truncate, sourceColor } from "../../lib/utils";

interface Props {
  event: Event;
  columnWidths?: Record<string, number>;
}

const ACTOR_COLORS: Record<string, string> = {
  agent: "text-accent",
  tool: "text-warn",
  human: "text-ok",
};

export function EventTickerRow({ event, columnWidths }: Props) {
  const isError = event.tool_status === "error";

  return (
    <div className={cn("data-row", isError && "!border-l-2 !border-l-err !pl-[14px]")}>
      <span className={cn("tabular-nums text-text-2", columnWidths?.time ? "" : "w-[80px] shrink-0")}
        style={columnWidths?.time ? { width: columnWidths.time, flexShrink: 0 } : undefined}
      >
        {formatTime(event.ts)}
      </span>
      <span className={cn("flex items-center gap-1.5", columnWidths?.source ? "" : "w-[60px] shrink-0")}
        style={columnWidths?.source ? { width: columnWidths.source, flexShrink: 0 } : undefined}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(event.source))} />
        <span className="truncate text-text-3">{event.source}</span>
      </span>
      <span className={cn(
        "font-semibold uppercase",
        ACTOR_COLORS[event.actor] ?? "text-text-2",
        columnWidths?.actor ? "" : "w-[50px] shrink-0",
      )}
        style={columnWidths?.actor ? { width: columnWidths.actor, flexShrink: 0 } : undefined}
      >
        {event.actor}
      </span>
      <span className={cn(
        "min-w-0 flex-1 truncate",
        isError ? "text-err" : "text-text-1",
      )}>
        {truncate(event.content, 120)}
      </span>
      <span className={cn("truncate text-text-3", columnWidths?.tool ? "" : "w-[80px] shrink-0")}
        style={columnWidths?.tool ? { width: columnWidths.tool, flexShrink: 0 } : undefined}
      >
        {event.tool_name ?? ""}
      </span>
      <span className={cn(
        "text-right text-[10px] font-semibold uppercase",
        isError ? "text-err" : event.tool_status === "ok" ? "text-ok" : "text-text-3",
        columnWidths?.status ? "" : "w-[60px] shrink-0",
      )}
        style={columnWidths?.status ? { width: columnWidths.status, flexShrink: 0 } : undefined}
      >
        {event.tool_status ?? ""}
      </span>
    </div>
  );
}
