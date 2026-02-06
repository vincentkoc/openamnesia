import { cn } from "../../lib/utils";
import type { Event } from "../../lib/api";
import { formatTime, truncate } from "../../lib/utils";
import { SourceBadge } from "../common/SourceBadge";
import { Badge } from "../common/Badge";
import { Bot, User, Wrench } from "lucide-react";

interface EventRowProps {
  event: Event;
}

const actorIcon: Record<string, React.ReactNode> = {
  human: <User className="h-3.5 w-3.5" />,
  agent: <Bot className="h-3.5 w-3.5" />,
  tool: <Wrench className="h-3.5 w-3.5" />,
};

export function EventRow({ event }: EventRowProps) {
  return (
    <div className="flex items-start gap-3 border-b border-cream-200 px-4 py-3 last:border-b-0 hover:bg-cream-50 transition-colors">
      {/* Turn index */}
      <span className="mt-0.5 w-6 shrink-0 text-right font-mono text-[11px] tabular-nums text-cream-500">
        {event.turn_index}
      </span>

      {/* Actor icon */}
      <span className={cn("mt-0.5 shrink-0", event.actor === "human" ? "text-accent-500" : "text-ink-50")}>
        {actorIcon[event.actor] ?? actorIcon.tool}
      </span>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-medium capitalize text-ink-200">
            {event.actor}
          </span>
          <SourceBadge source={event.source} />
          <span className="text-[11px] text-cream-500">{formatTime(event.ts)}</span>
          {event.tool_name && (
            <Badge variant={event.tool_status === "error" ? "error" : "default"}>
              {event.tool_name}
              {event.tool_status === "error" && " (err)"}
            </Badge>
          )}
        </div>
        <p className="mt-0.5 whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-ink-100">
          {truncate(event.content, 500)}
        </p>
      </div>
    </div>
  );
}
