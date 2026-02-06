import { useQuery } from "@tanstack/react-query";
import { Activity, Brain, Cpu, Database, Layers, Zap } from "lucide-react";
import { api } from "../lib/api";
import { numberFormat } from "../lib/utils";
import { StatsCard } from "../components/common/StatsCard";
import { EmptyState } from "../components/common/EmptyState";
import { TimelineChart } from "../components/timeline/TimelineChart";
import { MomentCard } from "../components/timeline/MomentCard";
import { SourceBadge } from "../components/common/SourceBadge";
import { useState } from "react";

export function StreamPage() {
  const [sourceFilter, setSourceFilter] = useState<string>("");

  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const { data: timeline } = useQuery({
    queryKey: ["timeline"],
    queryFn: () => api.timeline({ granularity: "hour" }),
  });
  const { data: moments } = useQuery({
    queryKey: ["moments", sourceFilter],
    queryFn: () => api.moments({ source: sourceFilter || undefined, limit: 30 }),
  });

  const sources = stats?.sources ?? [];

  return (
    <div className="px-8 py-6">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-[22px] font-semibold tracking-tight text-ink-500">
          Memory Stream
        </h1>
        <p className="mt-0.5 text-[13px] text-ink-50">
          Real-time flow of ingested events, sessions, and moments
        </p>
      </div>

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatsCard
          label="Events"
          value={numberFormat(stats?.total_events ?? 0)}
          icon={<Database className="h-4 w-4" />}
        />
        <StatsCard
          label="Sessions"
          value={numberFormat(stats?.total_sessions ?? 0)}
          icon={<Layers className="h-4 w-4" />}
        />
        <StatsCard
          label="Moments"
          value={numberFormat(stats?.total_moments ?? 0)}
          icon={<Zap className="h-4 w-4" />}
        />
        <StatsCard
          label="Skills"
          value={numberFormat(stats?.total_skills ?? 0)}
          icon={<Brain className="h-4 w-4" />}
        />
        <StatsCard
          label="Entities"
          value={numberFormat(stats?.total_entities ?? 0)}
          icon={<Cpu className="h-4 w-4" />}
        />
        <StatsCard
          label="24h Events"
          value={numberFormat(stats?.recent_events_24h ?? 0)}
          sub="last 24 hours"
          icon={<Activity className="h-4 w-4" />}
        />
      </div>

      {/* Timeline chart */}
      <div className="mb-6 rounded-xl border border-cream-300 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-ink-400">Activity Timeline</h2>
          <div className="flex items-center gap-2">
            {sources.map((s) => (
              <SourceBadge key={s.source} source={s.source} />
            ))}
          </div>
        </div>
        <TimelineChart data={timeline?.items ?? []} />
      </div>

      {/* Source filter + Moments */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-ink-400">Moments</h2>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setSourceFilter("")}
            className={`rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors ${
              !sourceFilter
                ? "bg-cream-300 text-ink-400"
                : "text-ink-50 hover:bg-cream-200"
            }`}
          >
            All
          </button>
          {sources.map((s) => (
            <button
              key={s.source}
              onClick={() => setSourceFilter(s.source === sourceFilter ? "" : s.source)}
              className={`rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors ${
                sourceFilter === s.source
                  ? "bg-cream-300 text-ink-400"
                  : "text-ink-50 hover:bg-cream-200"
              }`}
            >
              {s.source}
            </button>
          ))}
        </div>
      </div>

      {/* Moments list */}
      {moments && moments.items.length > 0 ? (
        <div className="grid gap-3">
          {moments.items.map((m) => (
            <MomentCard key={m.moment_id} moment={m} />
          ))}
          {moments.total > moments.items.length && (
            <div className="py-4 text-center text-[12px] text-ink-50">
              Showing {moments.items.length} of {moments.total} moments
            </div>
          )}
        </div>
      ) : (
        <EmptyState
          title="No moments yet"
          description="Moments will appear here as the daemon processes ingested events into meaningful segments."
        />
      )}
    </div>
  );
}
