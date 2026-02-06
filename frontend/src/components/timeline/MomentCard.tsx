import type { Moment } from "../../lib/api";
import { cn, frictionLabel, frictionColor, formatTime, truncate, sourceColor } from "../../lib/utils";

interface Props {
  moment: Moment;
  index: number;
  selected?: boolean;
  onSelect: (id: string) => void;
}

export function MomentCard({ moment, index, selected, onSelect }: Props) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(moment.moment_id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(moment.moment_id);
        }
      }}
      className={cn("data-row", selected && "selected")}
    >
      {/* TIME (80px) */}
      <span className="w-[80px] shrink-0 tabular-nums text-text-2">
        {moment.session_start_ts ? formatTime(moment.session_start_ts) : "--:--:--"}
      </span>

      {/* SOURCE (60px) */}
      <span className="flex w-[60px] shrink-0 items-center gap-1.5">
        <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(moment.source ?? ""))} />
        <span className="text-text-3 truncate">{moment.source ?? ""}</span>
      </span>

      {/* INTENT (flex) */}
      <span className={cn(
        "min-w-0 flex-1 truncate font-medium",
        selected ? "text-accent" : "text-text-0",
      )}>
        {truncate(moment.intent ?? "", 80)}
      </span>

      {/* OUTCOME (200px) */}
      <span className="w-[200px] shrink-0 truncate text-text-2">
        {truncate(moment.outcome ?? "", 50)}
      </span>

      {/* TURNS (80px) */}
      <span className="w-[80px] shrink-0 tabular-nums text-text-3 text-right">
        {moment.end_turn - moment.start_turn + 1} turns
      </span>

      {/* FRICTION (60px) */}
      <span className={cn(
        "w-[60px] shrink-0 text-right text-[10px] font-semibold uppercase tracking-wider",
        frictionColor(moment.friction_score),
      )}>
        {frictionLabel(moment.friction_score)}
      </span>

      {/* SESSION (80px) */}
      <span className="w-[80px] shrink-0 truncate text-right text-[10px] tabular-nums text-text-3">
        {moment.session_key.slice(0, 12)}
      </span>
    </div>
  );
}
