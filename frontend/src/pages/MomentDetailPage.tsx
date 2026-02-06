import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Target, Zap, AlertTriangle, Clock, Layers } from "lucide-react";
import { api } from "../lib/api";
import { frictionBg, frictionColor, formatDateTime } from "../lib/utils";
import { cn } from "../lib/utils";
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
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent-500 border-t-transparent" />
      </div>
    );
  }

  if (!moment) {
    return (
      <div className="px-8 py-6">
        <div className="text-[13px] text-ink-50">Moment not found.</div>
      </div>
    );
  }

  return (
    <div className="px-8 py-6">
      {/* Back link */}
      <Link
        to="/stream"
        className="mb-4 inline-flex items-center gap-1.5 text-[13px] text-ink-50 hover:text-ink-300 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to stream
      </Link>

      {/* Header */}
      <div className="mb-6 rounded-xl border border-cream-300 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <div className="flex items-center gap-2 mb-3">
          {moment.source && <SourceBadge source={moment.source} />}
          {moment.session_start_ts && (
            <span className="text-[12px] text-ink-50">
              {formatDateTime(moment.session_start_ts)}
            </span>
          )}
          {moment.friction_score !== null && moment.friction_score > 0 && (
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[12px] font-medium",
                frictionBg(moment.friction_score),
                frictionColor(moment.friction_score),
              )}
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              Friction: {(moment.friction_score * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {/* Intent */}
        {moment.intent && (
          <div className="flex items-center gap-2 text-[16px] font-semibold text-ink-500">
            <Target className="h-5 w-5 shrink-0 text-accent-500" />
            {moment.intent}
          </div>
        )}

        {/* Summary */}
        {moment.summary && (
          <p className="mt-2 text-[14px] leading-relaxed text-ink-100">
            {moment.summary}
          </p>
        )}

        {/* Outcome */}
        {moment.outcome && (
          <div className="mt-3 flex items-center gap-2 text-[13px] text-ink-50">
            <Zap className="h-4 w-4 text-warning-500" />
            <span className="font-medium">Outcome:</span> {moment.outcome}
          </div>
        )}

        {/* Meta row */}
        <div className="mt-4 flex items-center gap-4 text-[12px] text-ink-50">
          <div className="flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5" />
            Turns {moment.start_turn}&ndash;{moment.end_turn}
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            {moment.end_turn - moment.start_turn + 1} steps
          </div>
          <Badge variant="accent">{moment.session_key}</Badge>
        </div>
      </div>

      {/* Evidence */}
      {moment.evidence_json && Object.keys(moment.evidence_json).length > 0 && (
        <div className="mb-6 rounded-xl border border-cream-300 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <h3 className="mb-3 text-[13px] font-semibold text-ink-400">Evidence</h3>
          <pre className="overflow-x-auto rounded-lg bg-cream-50 p-3 font-mono text-[11px] text-ink-100">
            {JSON.stringify(moment.evidence_json, null, 2)}
          </pre>
        </div>
      )}

      {/* Artifacts */}
      {moment.artifacts_json && Object.keys(moment.artifacts_json).length > 0 && (
        <div className="mb-6 rounded-xl border border-cream-300 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <h3 className="mb-3 text-[13px] font-semibold text-ink-400">Artifacts</h3>
          <pre className="overflow-x-auto rounded-lg bg-cream-50 p-3 font-mono text-[11px] text-ink-100">
            {JSON.stringify(moment.artifacts_json, null, 2)}
          </pre>
        </div>
      )}

      {/* Events */}
      <div className="rounded-xl border border-cream-300 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <div className="border-b border-cream-200 px-5 py-3">
          <h3 className="text-[13px] font-semibold text-ink-400">
            Events ({moment.events?.length ?? 0})
          </h3>
        </div>
        {moment.events && moment.events.length > 0 ? (
          <div className="divide-y divide-cream-200">
            {moment.events.map((ev) => (
              <EventRow key={ev.event_id} event={ev} />
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-[13px] text-ink-50">No events found.</div>
        )}
      </div>
    </div>
  );
}
