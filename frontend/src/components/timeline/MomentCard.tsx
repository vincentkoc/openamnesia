import { Link } from "react-router-dom";
import { ChevronRight, Zap, Target, AlertTriangle } from "lucide-react";
import type { Moment } from "../../lib/api";
import { cn, frictionBg, frictionColor, timeAgo, truncate } from "../../lib/utils";
import { SourceBadge } from "../common/SourceBadge";

interface MomentCardProps {
  moment: Moment;
}

export function MomentCard({ moment }: MomentCardProps) {
  const hasFriction = moment.friction_score !== null && moment.friction_score > 0;

  return (
    <Link
      to={`/moments/${moment.moment_id}`}
      className="group block animate-fade-in rounded-xl border border-cream-300 bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:border-cream-400 hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 mb-1.5">
            {moment.source && <SourceBadge source={moment.source} />}
            {moment.session_start_ts && (
              <span className="text-[11px] text-ink-50">
                {timeAgo(moment.session_start_ts)}
              </span>
            )}
            {hasFriction && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium",
                  frictionBg(moment.friction_score),
                  frictionColor(moment.friction_score),
                )}
              >
                <AlertTriangle className="h-3 w-3" />
                {(moment.friction_score! * 100).toFixed(0)}%
              </span>
            )}
          </div>

          {/* Intent */}
          {moment.intent && (
            <div className="flex items-center gap-1.5 text-[13px] font-medium text-ink-400">
              <Target className="h-3.5 w-3.5 shrink-0 text-accent-500" />
              {truncate(moment.intent, 100)}
            </div>
          )}

          {/* Summary */}
          {moment.summary && (
            <p className="mt-1 text-[13px] leading-relaxed text-ink-50">
              {truncate(moment.summary, 180)}
            </p>
          )}

          {/* Outcome */}
          {moment.outcome && (
            <div className="mt-2 flex items-center gap-1.5 text-[12px] text-ink-50">
              <Zap className="h-3 w-3 text-warning-500" />
              <span>{truncate(moment.outcome, 120)}</span>
            </div>
          )}
        </div>

        <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-cream-400 transition-colors group-hover:text-ink-50" />
      </div>

      {/* Turn range indicator */}
      <div className="mt-3 flex items-center gap-2">
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-cream-200">
          <div
            className="h-full rounded-full bg-accent-400 transition-all"
            style={{ width: `${Math.min((moment.end_turn - moment.start_turn + 1) * 8, 100)}%` }}
          />
        </div>
        <span className="text-[10px] tabular-nums text-cream-500">
          {moment.end_turn - moment.start_turn + 1} turns
        </span>
      </div>
    </Link>
  );
}
