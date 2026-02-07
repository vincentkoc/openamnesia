import type { Moment } from "../../lib/api";
import { cn, frictionLabel, frictionColor, formatTime, truncate, sourceColor } from "../../lib/utils";

interface Props {
  moment: Moment;
  index: number;
  selected?: boolean;
  onSelect: (id: string) => void;
  variant?: "row" | "card";
  columnWidths?: Record<string, number>;
}

export function MomentCard({ moment, index, selected, onSelect, variant = "row", columnWidths }: Props) {
  const handleClick = () => onSelect(moment.moment_id);
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleClick(); }
  };

  if (variant === "card") {
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKey}
        className={cn(
          "card cursor-pointer rounded-lg border border-line/40 bg-void-1/60 p-3",
          selected && "border-accent bg-accent-dim",
        )}
      >
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className={cn("h-2 w-2 rounded-full", sourceColor(moment.source ?? ""))} />
            <span className="font-mono text-[10px] tabular-nums text-text-3">
              {moment.session_start_ts ? formatTime(moment.session_start_ts) : "--:--"}
            </span>
            <span className="text-[9px] uppercase text-text-3">{moment.source}</span>
          </div>
          <span className={cn("text-[9px] font-semibold uppercase", frictionColor(moment.friction_score))}>
            {frictionLabel(moment.friction_score)}
          </span>
        </div>
        <div className="mb-1.5 font-mono text-[12px] font-medium leading-snug text-text-0">
          {truncate(moment.intent ?? "", 60)}
        </div>
        <div className="font-mono text-[10px] leading-relaxed text-text-2">
          {truncate(moment.outcome ?? "", 80)}
        </div>
        <div className="mt-2 flex items-center justify-between border-t border-line/20 pt-2">
          <span className="font-mono text-[9px] tabular-nums text-text-3">
            {moment.end_turn - moment.start_turn + 1} turns
          </span>
          <span className="font-mono text-[9px] tabular-nums text-text-3">
            {moment.session_key.slice(0, 12)}
          </span>
        </div>
      </div>
    );
  }

  // Row variant
  const w = (key: string, fallback: string) =>
    columnWidths?.[key]
      ? { style: { width: columnWidths[key], flexShrink: 0 } }
      : { className: fallback };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKey}
      className={cn("data-row", selected && "selected")}
    >
      <span {...w("time", "w-[80px] shrink-0")} className={cn("tabular-nums text-text-2", columnWidths?.time ? "" : "w-[80px] shrink-0")}>
        {moment.session_start_ts ? formatTime(moment.session_start_ts) : "--:--:--"}
      </span>
      <span className={cn("flex items-center gap-1.5", columnWidths?.source ? "" : "w-[60px] shrink-0")}
        style={columnWidths?.source ? { width: columnWidths.source, flexShrink: 0 } : undefined}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(moment.source ?? ""))} />
        <span className="truncate text-text-3">{moment.source ?? ""}</span>
      </span>
      <span className={cn(
        "min-w-0 flex-1 truncate font-medium",
        selected ? "text-accent" : "text-text-0",
      )}>
        {truncate(moment.intent ?? "", 80)}
      </span>
      <span className={cn("truncate text-text-2", columnWidths?.outcome ? "" : "w-[200px] shrink-0")}
        style={columnWidths?.outcome ? { width: columnWidths.outcome, flexShrink: 0 } : undefined}
      >
        {truncate(moment.outcome ?? "", 50)}
      </span>
      <span className={cn("tabular-nums text-text-3 text-right", columnWidths?.turns ? "" : "w-[80px] shrink-0")}
        style={columnWidths?.turns ? { width: columnWidths.turns, flexShrink: 0 } : undefined}
      >
        {moment.end_turn - moment.start_turn + 1} turns
      </span>
      <span className={cn(
        "text-right text-[10px] font-semibold uppercase tracking-wider",
        frictionColor(moment.friction_score),
        columnWidths?.friction ? "" : "w-[60px] shrink-0",
      )}
        style={columnWidths?.friction ? { width: columnWidths.friction, flexShrink: 0 } : undefined}
      >
        {frictionLabel(moment.friction_score)}
      </span>
      <span className={cn("truncate text-right text-[10px] tabular-nums text-text-3", columnWidths?.session ? "" : "w-[80px] shrink-0")}
        style={columnWidths?.session ? { width: columnWidths.session, flexShrink: 0 } : undefined}
      >
        {moment.session_key.slice(0, 12)}
      </span>
    </div>
  );
}
