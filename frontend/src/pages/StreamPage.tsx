import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { numberFormat } from "../lib/utils";
import { StatsCard } from "../components/common/StatsCard";
import { EmptyState } from "../components/common/EmptyState";
import { TimelineChart } from "../components/timeline/TimelineChart";
import { MomentCard } from "../components/timeline/MomentCard";
import { SourceBadge } from "../components/common/SourceBadge";
import { useState } from "react";

export function StreamPage() {
  const [src, setSrc] = useState("");

  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const { data: tl } = useQuery({ queryKey: ["timeline"], queryFn: () => api.timeline({ granularity: "hour" }) });
  const { data: moments } = useQuery({
    queryKey: ["moments", src],
    queryFn: () => api.moments({ source: src || undefined, limit: 30 }),
  });

  const sources = stats?.sources ?? [];

  return (
    <div>
      {/* Hero — editorial headline */}
      <div className="accent-strip mb-16 py-12 text-center">
        <h1 className="font-serif text-[48px] font-normal italic leading-none tracking-tight text-text-0">
          Memory Stream
        </h1>
        <p className="mt-3 text-[10px] uppercase tracking-[0.3em] text-text-3">
          traces &rarr; events &rarr; moments &rarr; skills
        </p>

        {/* Stats strip — big editorial numbers */}
        <div className="stagger mx-auto mt-10 flex max-w-2xl items-end justify-between border-t border-b border-line/50 py-6">
          <StatsCard label="events" value={numberFormat(stats?.total_events ?? 0)} />
          <div className="h-8 w-px bg-line/30" />
          <StatsCard label="sessions" value={numberFormat(stats?.total_sessions ?? 0)} />
          <div className="h-8 w-px bg-line/30" />
          <StatsCard label="moments" value={numberFormat(stats?.total_moments ?? 0)} />
          <div className="h-8 w-px bg-line/30" />
          <StatsCard label="skills" value={numberFormat(stats?.total_skills ?? 0)} />
          <div className="h-8 w-px bg-line/30" />
          <StatsCard label="24h" value={numberFormat(stats?.recent_events_24h ?? 0)} />
        </div>
      </div>

      {/* Timeline heat strip */}
      <div className="mb-12">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[9px] font-medium uppercase tracking-[0.2em] text-text-3">
            Activity &mdash; 24h
          </span>
          <div className="flex items-center gap-2">
            {sources.map((s) => (
              <SourceBadge key={s.source} source={s.source} />
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-line/40 bg-void-1/50 p-5">
          <TimelineChart data={tl?.items ?? []} />
        </div>
      </div>

      {/* Divider with filter */}
      <div className="mb-8 flex items-center gap-4">
        <div className="h-px flex-1 bg-line/30" />
        <div className="flex items-center gap-1">
          <button
            onClick={() => setSrc("")}
            className={`rounded px-2.5 py-1 text-[9px] font-medium uppercase tracking-[0.15em] transition-colors ${
              !src ? "bg-accent text-void-0" : "text-text-3 hover:text-text-1"
            }`}
          >
            all
          </button>
          {sources.map((s) => (
            <button
              key={s.source}
              onClick={() => setSrc(s.source === src ? "" : s.source)}
              className={`rounded px-2.5 py-1 text-[9px] font-medium uppercase tracking-[0.15em] transition-colors ${
                src === s.source ? "bg-accent text-void-0" : "text-text-3 hover:text-text-1"
              }`}
            >
              {s.source}
            </button>
          ))}
        </div>
        <div className="h-px flex-1 bg-line/30" />
      </div>

      {/* Section header */}
      <div className="mb-6 flex items-baseline justify-between">
        <h2 className="font-serif text-[24px] italic text-text-0">
          Moments
        </h2>
        <span className="text-[9px] tabular-nums uppercase tracking-[0.2em] text-text-3">
          {moments?.total ?? 0} total
        </span>
      </div>

      {/* Moments trace */}
      {moments && moments.items.length > 0 ? (
        <div className="pl-2">
          {moments.items.map((m, i) => (
            <MomentCard key={m.moment_id} moment={m} index={i} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No moments yet"
          description="Moments appear as the daemon processes ingested events."
        />
      )}
    </div>
  );
}
