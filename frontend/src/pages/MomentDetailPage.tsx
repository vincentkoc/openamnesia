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
      <div className="flex h-[60vh] items-center justify-center">
        <div className="h-3 w-3 rounded-full bg-accent anim-pulse" />
      </div>
    );
  }

  if (!moment) {
    return <div className="py-16 text-center text-[11px] uppercase tracking-widest text-text-3">moment not found</div>;
  }

  return (
    <div>
      {/* Back */}
      <Link to="/stream" className="mb-6 inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.15em] text-text-3 transition-colors hover:text-accent">
        &larr; Stream
      </Link>

      {/* Hero */}
      <div className="accent-strip mb-10 py-8 text-center">
        <div className="mb-4 flex items-center justify-center gap-3 text-[9px]">
          {moment.source && <SourceBadge source={moment.source} />}
          {moment.session_start_ts && (
            <span className="tabular-nums text-text-3">{formatDateTime(moment.session_start_ts)}</span>
          )}
          <span className={cn("flex items-center gap-1.5 font-semibold uppercase tracking-[0.15em]", frictionColor(moment.friction_score))}>
            <span className={cn("h-2 w-2 rounded-full", frictionDotColor(moment.friction_score))} />
            {frictionLabel(moment.friction_score)}
          </span>
        </div>

        {moment.intent && (
          <h1 className="mx-auto max-w-2xl font-serif text-[36px] italic leading-snug tracking-tight text-text-0">
            {moment.intent}
          </h1>
        )}

        {moment.summary && (
          <p className="mx-auto mt-4 max-w-xl text-[12px] leading-relaxed text-text-2">
            {moment.summary}
          </p>
        )}

        {moment.outcome && (
          <div className="mx-auto mt-5 max-w-lg rounded-md bg-ok-dim px-4 py-2.5 text-[11px]">
            <span className="mr-1 font-bold text-ok">+</span>
            <span className="text-text-0">{moment.outcome}</span>
          </div>
        )}

        <div className="mt-5 flex items-center justify-center gap-4 text-[9px] text-text-3">
          <span className="tabular-nums">turns {moment.start_turn}&ndash;{moment.end_turn}</span>
          <span>&middot;</span>
          <span className="tabular-nums">{moment.end_turn - moment.start_turn + 1} steps</span>
          <span>&middot;</span>
          <Badge variant="accent">{moment.session_key}</Badge>
        </div>
      </div>

      {/* Evidence & Artifacts */}
      {(Object.keys(moment.evidence_json || {}).length > 0 || Object.keys(moment.artifacts_json || {}).length > 0) && (
        <div className="mb-8 grid gap-5 sm:grid-cols-2">
          {moment.evidence_json && Object.keys(moment.evidence_json).length > 0 && (
            <div className="rounded-lg border border-line/40 bg-void-1/50 p-5">
              <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.2em] text-text-3">Evidence</div>
              <pre className="overflow-x-auto text-[10px] leading-relaxed text-text-2">
{JSON.stringify(moment.evidence_json, null, 2)}</pre>
            </div>
          )}
          {moment.artifacts_json && Object.keys(moment.artifacts_json).length > 0 && (
            <div className="rounded-lg border border-line/40 bg-void-1/50 p-5">
              <div className="mb-3 text-[9px] font-semibold uppercase tracking-[0.2em] text-text-3">Artifacts</div>
              <pre className="overflow-x-auto text-[10px] leading-relaxed text-text-2">
{JSON.stringify(moment.artifacts_json, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Events — diff view */}
      <div className="mb-4 flex items-center gap-4">
        <div className="h-px flex-1 bg-line/30" />
        <span className="text-[9px] uppercase tracking-[0.2em] text-text-3">
          Events &middot; {moment.events?.length ?? 0} turns
        </span>
        <div className="h-px flex-1 bg-line/30" />
      </div>

      <div className="overflow-hidden rounded-lg border border-line/40 bg-void-1/50">
        {moment.events && moment.events.length > 0 ? (
          <div>
            {moment.events.map((ev) => (
              <EventRow key={ev.event_id} event={ev} />
            ))}
          </div>
        ) : (
          <div className="py-10 text-center text-[10px] uppercase tracking-widest text-text-3">no events</div>
        )}
      </div>
    </div>
  );
}
