import { Link } from "react-router-dom";
import type { Moment } from "../../lib/api";
import { cn, frictionLabel, frictionColor, frictionDotColor, timeAgo, truncate } from "../../lib/utils";
import { SourceBadge } from "../common/SourceBadge";

interface Props {
  moment: Moment;
  index: number;
}

export function MomentCard({ moment, index }: Props) {
  return (
    <Link
      to={`/moments/${moment.moment_id}`}
      className="group anim-fade flex gap-5"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Timeline spine */}
      <div className="flex flex-col items-center pt-2">
        <div className={cn(
          "h-3 w-3 rounded-full ring-[3px] ring-void-0 transition-all group-hover:ring-accent/20",
          frictionDotColor(moment.friction_score),
        )} />
        <div className="w-px flex-1 bg-gradient-to-b from-line via-line/50 to-transparent" />
      </div>

      {/* Content */}
      <div className="card mb-6 flex-1 rounded-lg border border-line/40 bg-void-1/60 p-5 backdrop-blur-sm">
        {/* Top row */}
        <div className="flex items-center gap-2.5 text-[9px]">
          {moment.source && <SourceBadge source={moment.source} />}
          {moment.session_start_ts && (
            <span className="tabular-nums text-text-3">{timeAgo(moment.session_start_ts)}</span>
          )}
          <span className="ml-auto flex items-center gap-1.5">
            <span className={cn("uppercase tracking-[0.15em] font-semibold", frictionColor(moment.friction_score))}>
              {frictionLabel(moment.friction_score)}
            </span>
          </span>
          <span className="tabular-nums text-text-3">
            {moment.end_turn - moment.start_turn + 1} turns
          </span>
        </div>

        {/* Intent — editorial serif headline */}
        {moment.intent && (
          <h3 className="mt-3 font-serif text-[18px] italic leading-snug text-text-0 transition-colors group-hover:text-accent">
            {truncate(moment.intent, 100)}
          </h3>
        )}

        {/* Summary */}
        {moment.summary && (
          <p className="mt-2 text-[11px] leading-relaxed text-text-2">
            {truncate(moment.summary, 200)}
          </p>
        )}

        {/* Outcome — diff-style addition line */}
        {moment.outcome && (
          <div className="mt-3 border-l-2 border-ok/40 pl-3 text-[10px] text-text-1">
            <span className="mr-1 font-bold text-ok">+</span>
            {truncate(moment.outcome, 120)}
          </div>
        )}

        {/* Activity bar */}
        <div className="mt-4 h-[2px] overflow-hidden rounded-full bg-void-3">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min((moment.end_turn - moment.start_turn + 1) * 10, 100)}%`,
              background: `linear-gradient(90deg, ${srcHex(moment.source)} 0%, transparent 100%)`,
              opacity: 0.5,
            }}
          />
        </div>
      </div>
    </Link>
  );
}

function srcHex(src?: string): string {
  const map: Record<string, string> = {
    cursor: "#5B9EFF", codex: "#FF6BC1", terminal: "#FFD93D",
    imessage: "#3DDC84", slack: "#B794F6", discord: "#7B8CFF",
  };
  return map[src ?? ""] ?? "#E8562A";
}
