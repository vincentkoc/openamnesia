import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { cn, frictionLabel, frictionColor, formatDateTime } from "../../lib/utils";
import { SourceBadge } from "../common/SourceBadge";
import { EventRow } from "./EventRow";

interface Props {
  momentId: string;
  onClose: () => void;
}

export function MomentPanel({ momentId, onClose }: Props) {
  const { data: moment, isLoading } = useQuery({
    queryKey: ["moment", momentId],
    queryFn: () => api.moment(momentId),
  });

  return (
    <div className="anim-slide-in flex h-full w-[560px] shrink-0 flex-col border-l border-line/50 bg-void-0"
      style={{ boxShadow: "var(--panel-shadow)" }}
    >
      {/* Panel header */}
      <div className="flex shrink-0 items-center justify-between border-b border-line/30 px-4 py-2.5">
        <span className="font-sans text-[9px] font-semibold uppercase tracking-[0.2em] text-text-3">
          moment detail
        </span>
        <button
          onClick={onClose}
          className="rounded px-2 py-0.5 font-sans text-[10px] text-text-3 transition-colors hover:bg-void-2 hover:text-text-0"
        >
          &times; close
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex h-32 items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-accent anim-pulse" />
          </div>
        )}

        {moment && (
          <div className="anim-fade-in">
            {/* Stats strip */}
            <div className="flex flex-wrap items-center gap-4 border-b border-line/30 bg-void-1/50 px-4 py-2.5">
              <div className="stat-pip">
                <span className="stat-value">{moment.end_turn - moment.start_turn + 1}</span>
                <span className="stat-label">turns</span>
              </div>
              <div className="stat-pip">
                <span className="stat-value">{moment.end_turn - moment.start_turn + 1}</span>
                <span className="stat-label">steps</span>
              </div>
              <div className="stat-pip">
                <span className={cn("stat-value", frictionColor(moment.friction_score))}>
                  {frictionLabel(moment.friction_score)}
                </span>
                <span className="stat-label">friction</span>
              </div>
              {moment.source && <SourceBadge source={moment.source} />}
              {moment.session_start_ts && (
                <span className="font-mono text-[10px] tabular-nums text-text-3">
                  {formatDateTime(moment.session_start_ts)}
                </span>
              )}
              <span className="font-mono text-[10px] tabular-nums text-accent">
                {moment.session_key}
              </span>
            </div>

            {/* Intent */}
            {moment.intent && (
              <div className="border-b border-line/20 px-4 py-3">
                <div className="mb-1 font-sans text-[9px] font-semibold uppercase tracking-[0.15em] text-text-3">
                  Intent
                </div>
                <div className="font-mono text-[13px] font-medium text-text-0">
                  {moment.intent}
                </div>
              </div>
            )}

            {/* Summary */}
            {moment.summary && (
              <div className="border-b border-line/20 px-4 py-3">
                <div className="mb-1 font-sans text-[9px] font-semibold uppercase tracking-[0.15em] text-text-3">
                  Summary
                </div>
                <div className="font-mono text-[11px] leading-relaxed text-text-2">
                  {moment.summary}
                </div>
              </div>
            )}

            {/* Outcome */}
            {moment.outcome && (
              <div className="border-b border-line/20 px-4 py-3">
                <div className="mb-1 font-sans text-[9px] font-semibold uppercase tracking-[0.15em] text-text-3">
                  Outcome
                </div>
                <div className="font-mono text-[11px] text-ok/80">
                  {moment.outcome}
                </div>
              </div>
            )}

            {/* Evidence & Artifacts */}
            {(Object.keys(moment.evidence_json || {}).length > 0 ||
              Object.keys(moment.artifacts_json || {}).length > 0) && (
              <div className="border-b border-line/20 px-4 py-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  {moment.evidence_json &&
                    Object.keys(moment.evidence_json).length > 0 && (
                      <div className="rounded border border-line/30 bg-void-1 p-3">
                        <div className="mb-1.5 font-sans text-[8px] font-semibold uppercase tracking-[0.2em] text-text-3">
                          evidence
                        </div>
                        <pre className="overflow-x-auto font-mono text-[9px] leading-relaxed text-text-2">
                          {JSON.stringify(moment.evidence_json, null, 2)}
                        </pre>
                      </div>
                    )}
                  {moment.artifacts_json &&
                    Object.keys(moment.artifacts_json).length > 0 && (
                      <div className="rounded border border-line/30 bg-void-1 p-3">
                        <div className="mb-1.5 font-sans text-[8px] font-semibold uppercase tracking-[0.2em] text-text-3">
                          artifacts
                        </div>
                        <pre className="overflow-x-auto font-mono text-[9px] leading-relaxed text-text-2">
                          {JSON.stringify(moment.artifacts_json, null, 2)}
                        </pre>
                      </div>
                    )}
                </div>
              </div>
            )}

            {/* Events */}
            <div className="px-4 py-3">
              <div className="mb-2 flex items-center gap-2">
                <div className="h-px flex-1 bg-line/20" />
                <span className="font-sans text-[8px] font-semibold uppercase tracking-[0.2em] text-text-3">
                  events &middot; {moment.events?.length ?? 0} turns
                </span>
                <div className="h-px flex-1 bg-line/20" />
              </div>

              {moment.events && moment.events.length > 0 ? (
                <div className="overflow-hidden rounded border border-line/30">
                  {moment.events.map((ev) => (
                    <EventRow key={ev.event_id} event={ev} />
                  ))}
                </div>
              ) : (
                <div className="py-6 text-center font-sans text-[9px] uppercase tracking-widest text-text-3">
                  no events
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
