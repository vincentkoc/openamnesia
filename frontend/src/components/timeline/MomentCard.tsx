import type { Moment } from "../../lib/api";
import { cn, frictionLabel, frictionColor, frictionDotColor, timeAgo, truncate } from "../../lib/utils";
import { SourceBadge } from "../common/SourceBadge";

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
      className={cn(
        "group anim-fade cursor-pointer border-b border-line/20 transition-colors outline-none",
        selected
          ? "bg-accent-dim/40 border-l-2 border-l-accent"
          : "hover:bg-void-1/50",
      )}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* Diff hunk header */}
      <div className={cn(
        "flex items-center gap-2 px-4 py-1.5 text-[9px]",
        selected ? "bg-accent-dim/50" : "bg-accent-dim/20",
      )}>
        <span className="font-bold text-accent">@@</span>
        {moment.source && <SourceBadge source={moment.source} />}
        {moment.session_start_ts && (
          <span className="tabular-nums text-text-3">
            {timeAgo(moment.session_start_ts)}
          </span>
        )}
        <span className="tabular-nums text-text-3">
          {moment.end_turn - moment.start_turn + 1} turns
        </span>
        <span className="ml-auto flex items-center gap-1.5">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              frictionDotColor(moment.friction_score),
            )}
          />
          <span
            className={cn(
              "font-semibold uppercase tracking-[0.15em]",
              frictionColor(moment.friction_score),
            )}
          >
            {frictionLabel(moment.friction_score)}
          </span>
        </span>
        <span className="font-bold text-accent">@@</span>
      </div>

      {/* Diff content lines */}
      <div className="px-4 py-3">
        {/* Intent as addition (+) */}
        {moment.intent && (
          <div className="flex gap-2">
            <span className="w-3 shrink-0 text-right font-bold text-ok">
              +
            </span>
            <span className={cn(
              "text-[12px] font-medium transition-colors",
              selected ? "text-accent" : "text-text-0 group-hover:text-accent",
            )}>
              {truncate(moment.intent, 120)}
            </span>
          </div>
        )}

        {/* Summary as context */}
        {moment.summary && (
          <div className="mt-1 flex gap-2">
            <span className="w-3 shrink-0 text-right text-text-3">&nbsp;</span>
            <span className="text-[11px] leading-relaxed text-text-2">
              {truncate(moment.summary, 200)}
            </span>
          </div>
        )}

        {/* Outcome as addition */}
        {moment.outcome && (
          <div className="mt-1 flex gap-2">
            <span className="w-3 shrink-0 text-right font-bold text-ok">
              +
            </span>
            <span className="text-[11px] text-ok/80">
              {truncate(moment.outcome, 140)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
