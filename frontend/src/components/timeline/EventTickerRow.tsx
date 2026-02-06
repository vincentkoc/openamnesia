import type { Event } from "../../lib/api";
import { cn, formatTime, truncate, sourceColor } from "../../lib/utils";

interface Props {
  event: Event;
}

const ACTOR_COLORS: Record<string, string> = {
  agent: "text-accent",
  tool: "text-warn",
  human: "text-ok",
};

export function EventTickerRow({ event }: Props) {
  const isError = event.tool_status === "error";

  return (
    <div className={cn("data-row", isError && "!border-l-2 !border-l-err !pl-[14px]")}>
      {/* TIME (80px) */}
      <span className="w-[80px] shrink-0 tabular-nums text-text-2">
        {formatTime(event.ts)}
      </span>

      {/* SOURCE (60px) */}
      <span className="flex w-[60px] shrink-0 items-center gap-1.5">
        <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(event.source))} />
        <span className="text-text-3 truncate">{event.source}</span>
      </span>

      {/* ACTOR (50px) */}
      <span className={cn(
        "w-[50px] shrink-0 font-semibold uppercase",
        ACTOR_COLORS[event.actor] ?? "text-text-2",
      )}>
        {event.actor}
      </span>

      {/* CONTENT (flex) */}
      <span className={cn(
        "min-w-0 flex-1 truncate",
        isError ? "text-err" : "text-text-1",
      )}>
        {truncate(event.content, 120)}
      </span>

      {/* TOOL (80px) */}
      <span className="w-[80px] shrink-0 truncate text-text-3">
        {event.tool_name ?? ""}
      </span>

      {/* STATUS (60px) */}
      <span className={cn(
        "w-[60px] shrink-0 text-right text-[10px] font-semibold uppercase",
        isError ? "text-err" : event.tool_status === "ok" ? "text-ok" : "text-text-3",
      )}>
        {event.tool_status ?? ""}
      </span>
    </div>
  );
}
