import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { cn, frictionLabel, frictionColor, frictionDotColor, formatDateTime } from "../lib/utils";
import { SourceBadge } from "../components/common/SourceBadge";
import { Badge } from "../components/common/Badge";
import { EventRow } from "../components/timeline/EventRow";

export function MomentDetailPage() {
  const { momentId } = useParams<{ momentId: string }>();

  const { data: moment, isLoading } = useQuery({
    queryKey: ["moment", momentId],
    queryFn: () => api.moment(momentId!),
    enabled: !!momentId,
  });

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-2 w-2 rounded-full bg-accent anim-pulse" />
      </div>
    );
  }

  if (!moment) {
    return (
      <div className="flex h-full items-center justify-center text-[10px] uppercase tracking-widest text-text-3">
        moment not found
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-[900px] px-6 py-8">
        {/* Back */}
        <Link
          to="/stream"
          className="mb-6 inline-flex items-center gap-1.5 text-[9px] uppercase tracking-[0.15em] text-text-3 transition-colors hover:text-accent"
        >
          &larr; stream
        </Link>

        {/* Diff-style header */}
        <div className="mb-6 overflow-hidden rounded border border-line/40">
          {/* Hunk header */}
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
            <span className="ml-auto tabular-nums text-text-3">
              turns {moment.start_turn}&ndash;{moment.end_turn} &middot;{" "}
              {moment.end_turn - moment.start_turn + 1} steps
            </span>
            <Badge variant="accent">{moment.session_key}</Badge>
            <span className="font-bold text-accent">@@</span>
          </div>

          {/* Content */}
          <div className="px-4 py-4">
            {moment.intent && (
              <div className="flex gap-2">
                <span className="w-3 shrink-0 text-right font-bold text-ok">
                  +
                </span>
                <span className="text-[16px] font-bold text-text-0">
                  {moment.intent}
                </span>
              </div>
            )}

            {moment.summary && (
              <div className="mt-2 flex gap-2">
                <span className="w-3 shrink-0 text-right text-text-3">
                  &nbsp;
                </span>
                <span className="text-[11px] leading-relaxed text-text-2">
                  {moment.summary}
                </span>
              </div>
            )}

            {moment.outcome && (
              <div className="mt-2 flex gap-2">
                <span className="w-3 shrink-0 text-right font-bold text-ok">
                  +
                </span>
                <span className="text-[11px] text-ok/80">
                  {moment.outcome}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Evidence & Artifacts */}
        {(Object.keys(moment.evidence_json || {}).length > 0 ||
          Object.keys(moment.artifacts_json || {}).length > 0) && (
          <div className="mb-6 grid gap-4 sm:grid-cols-2">
            {moment.evidence_json &&
              Object.keys(moment.evidence_json).length > 0 && (
                <div className="rounded border border-line/40 p-4">
                  <div className="mb-2 text-[9px] font-semibold uppercase tracking-[0.2em] text-text-3">
                    evidence
                  </div>
                  <pre className="overflow-x-auto text-[10px] leading-relaxed text-text-2">
                    {JSON.stringify(moment.evidence_json, null, 2)}
                  </pre>
                </div>
              )}
            {moment.artifacts_json &&
              Object.keys(moment.artifacts_json).length > 0 && (
                <div className="rounded border border-line/40 p-4">
                  <div className="mb-2 text-[9px] font-semibold uppercase tracking-[0.2em] text-text-3">
                    artifacts
                  </div>
                  <pre className="overflow-x-auto text-[10px] leading-relaxed text-text-2">
                    {JSON.stringify(moment.artifacts_json, null, 2)}
                  </pre>
                </div>
              )}
          </div>
        )}

        {/* Events */}
        <div className="mb-3 flex items-center gap-3">
          <div className="h-px flex-1 bg-line/30" />
          <span className="text-[9px] uppercase tracking-[0.2em] text-text-3">
            events &middot; {moment.events?.length ?? 0} turns
          </span>
          <div className="h-px flex-1 bg-line/30" />
        </div>

        <div className="overflow-hidden rounded border border-line/40">
          {moment.events && moment.events.length > 0 ? (
            <div>
              {moment.events.map((ev) => (
                <EventRow key={ev.event_id} event={ev} />
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-[10px] uppercase tracking-widest text-text-3">
              no events
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
