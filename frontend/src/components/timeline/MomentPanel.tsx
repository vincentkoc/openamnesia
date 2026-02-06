import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { cn, frictionLabel, frictionColor, frictionDotColor, formatDateTime } from "../../lib/utils";
import { SourceBadge } from "../common/SourceBadge";
import { Badge } from "../common/Badge";
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
    <div className="anim-slide-in flex h-full w-[520px] shrink-0 flex-col border-l border-line/50 bg-void-0"
      style={{ boxShadow: "var(--panel-shadow)" }}
    >
      {/* Panel header */}
      <div className="flex shrink-0 items-center justify-between border-b border-line/30 px-4 py-2.5">
        <span className="text-[9px] uppercase tracking-[0.2em] text-text-3">
          moment detail
        </span>
        <button
          onClick={onClose}
          className="rounded px-2 py-0.5 text-[10px] text-text-3 transition-colors hover:bg-void-2 hover:text-text-0"
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
            {/* Diff-style header */}
            <div className="flex items-center gap-2 bg-accent-dim/30 px-4 py-2 text-[9px]">
              <span className="font-bold text-accent">@@</span>
              {moment.source && <SourceBadge source={moment.source} />}
              {moment.session_start_ts && (
                <span className="tabular-nums text-text-3">
                  {formatDateTime(moment.session_start_ts)}
                </span>
              )}
              <span
                className={cn(
                  "flex items-center gap-1.5 font-semibold uppercase tracking-[0.15em]",
                  frictionColor(moment.friction_score),
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    frictionDotColor(moment.friction_score),
                  )}
                />
                {frictionLabel(moment.friction_score)}
              </span>
              <span className="font-bold text-accent">@@</span>
            </div>

            {/* Intent / Summary / Outcome */}
            <div className="border-b border-line/20 px-4 py-4">
              {moment.intent && (
                <div className="flex gap-2">
                  <span className="w-3 shrink-0 text-right font-bold text-ok">+</span>
                  <span className="text-[14px] font-bold text-text-0">
                    {moment.intent}
                  </span>
                </div>
              )}

              {moment.summary && (
                <div className="mt-2 flex gap-2">
                  <span className="w-3 shrink-0 text-right text-text-3">&nbsp;</span>
                  <span className="text-[11px] leading-relaxed text-text-2">
                    {moment.summary}
                  </span>
                </div>
              )}

              {moment.outcome && (
                <div className="mt-2 flex gap-2">
                  <span className="w-3 shrink-0 text-right font-bold text-ok">+</span>
                  <span className="text-[11px] text-ok/80">
                    {moment.outcome}
                  </span>
                </div>
              )}
            </div>

            {/* Meta strip */}
            <div className="flex items-center gap-3 border-b border-line/20 px-4 py-2 text-[9px]">
              <span className="tabular-nums text-text-3">
                turns {moment.start_turn}&ndash;{moment.end_turn}
              </span>
              <span className="text-line">&middot;</span>
              <span className="tabular-nums text-text-3">
                {moment.end_turn - moment.start_turn + 1} steps
              </span>
              <Badge variant="accent">{moment.session_key}</Badge>
            </div>

            {/* Evidence & Artifacts */}
            {(Object.keys(moment.evidence_json || {}).length > 0 ||
              Object.keys(moment.artifacts_json || {}).length > 0) && (
              <div className="border-b border-line/20 px-4 py-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  {moment.evidence_json &&
                    Object.keys(moment.evidence_json).length > 0 && (
                      <div className="rounded border border-line/30 bg-void-1 p-3">
                        <div className="mb-1.5 text-[8px] font-semibold uppercase tracking-[0.2em] text-text-3">
                          evidence
                        </div>
                        <pre className="overflow-x-auto text-[9px] leading-relaxed text-text-2">
                          {JSON.stringify(moment.evidence_json, null, 2)}
                        </pre>
                      </div>
                    )}
                  {moment.artifacts_json &&
                    Object.keys(moment.artifacts_json).length > 0 && (
                      <div className="rounded border border-line/30 bg-void-1 p-3">
                        <div className="mb-1.5 text-[8px] font-semibold uppercase tracking-[0.2em] text-text-3">
                          artifacts
                        </div>
                        <pre className="overflow-x-auto text-[9px] leading-relaxed text-text-2">
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
                <span className="text-[8px] uppercase tracking-[0.2em] text-text-3">
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
                <div className="py-6 text-center text-[9px] uppercase tracking-widest text-text-3">
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
