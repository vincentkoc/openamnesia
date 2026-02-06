import type { Event } from "../../lib/api";
import { cn, formatTime, truncate, sourceTextColor } from "../../lib/utils";
import { Badge } from "../common/Badge";

interface Props {
  event: Event;
}

export function EventRow({ event }: Props) {
  const isAgent = event.actor === "agent";
  const isTool = event.actor === "tool";
  const isError = event.tool_status === "error";

  return (
    <div className="group flex gap-3 border-b border-line/50 px-3 py-2.5 last:border-b-0 hover:bg-void-2/50 transition-colors">
      {/* Line number */}
      <span className="w-5 shrink-0 text-right text-[10px] tabular-nums text-text-3 pt-0.5">
        {event.turn_index}
      </span>

      {/* Diff gutter */}
      <span className={cn(
        "w-2 shrink-0 text-[11px] font-bold pt-0.5",
        isAgent ? "text-accent" : isTool ? "text-warn" : "text-ok",
      )}>
        {isAgent ? ">" : isTool ? "|" : "+"}
      </span>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[10px]">
          <span className={cn("font-semibold uppercase tracking-wider", sourceTextColor(event.source))}>
            {event.actor}
          </span>
          <span className="text-text-3 tabular-nums">{formatTime(event.ts)}</span>
          {event.tool_name && (
            <Badge variant={isError ? "err" : "default"}>
              {event.tool_name}
            </Badge>
          )}
        </div>
        <pre className={cn(
          "mt-1 whitespace-pre-wrap text-[11px] leading-relaxed",
          isError ? "text-err/80" : "text-text-1",
        )}>
          {truncate(event.content, 600)}
        </pre>
      </div>
    </div>
  );
}
