import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { numberFormat } from "../lib/utils";
import { TimelineChart } from "../components/timeline/TimelineChart";
import { MomentCard } from "../components/timeline/MomentCard";
import { MomentPanel } from "../components/timeline/MomentPanel";
import { SourceBadge } from "../components/common/SourceBadge";
import { EmptyState } from "../components/common/EmptyState";
import { useState, useCallback } from "react";

export function StreamPage() {
  const [src, setSrc] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const { data: tl } = useQuery({
    queryKey: ["timeline"],
    queryFn: () => api.timeline({ granularity: "hour" }),
  });
  const { data: moments } = useQuery({
    queryKey: ["moments", src],
    queryFn: () => api.moments({ source: src || undefined, limit: 50 }),
  });

  const sources = stats?.sources ?? [];

  const handleSelect = useCallback((id: string) => {
    setSelectedId((prev) => (prev === id ? null : id));
  }, []);

  const handleClose = useCallback(() => {
    setSelectedId(null);
  }, []);

  return (
    <div className="flex h-full">
      {/* Main content area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Stats bar */}
        <div className="flex shrink-0 items-center justify-between border-b border-line/30 px-6 py-2">
          <div className="flex items-center gap-6 text-[10px]">
            <Stat label="events" value={stats?.total_events ?? 0} />
            <Stat label="sessions" value={stats?.total_sessions ?? 0} />
            <Stat label="moments" value={stats?.total_moments ?? 0} />
            <Stat label="skills" value={stats?.total_skills ?? 0} />
            <Stat label="24h" value={stats?.recent_events_24h ?? 0} accent />
          </div>
          <div className="flex items-center gap-2">
            {sources.map((s) => (
              <SourceBadge key={s.source} source={s.source} />
            ))}
          </div>
        </div>

        {/* Full-bleed timeline chart */}
        <div className="shrink-0 border-b border-line/30">
          <TimelineChart data={tl?.items ?? []} />
        </div>

        {/* Filter bar */}
        <div className="flex shrink-0 items-center gap-1 border-b border-line/20 px-6 py-1.5">
          <span className="mr-2 text-[9px] uppercase tracking-[0.2em] text-text-3">
            filter:
          </span>
          <FilterBtn active={!src} onClick={() => setSrc("")}>
            all
          </FilterBtn>
          {sources.map((s) => (
            <FilterBtn
              key={s.source}
              active={src === s.source}
              onClick={() => setSrc(s.source === src ? "" : s.source)}
            >
              {s.source}
            </FilterBtn>
          ))}
          <span className="ml-auto text-[9px] tabular-nums tracking-wider text-text-3">
            {moments?.total ?? 0} moments
          </span>
        </div>

        {/* Scrollable moments */}
        <div className="relative min-h-0 flex-1 overflow-y-auto">
          {moments && moments.items.length > 0 ? (
            <div>
              {moments.items.map((m, i) => (
                <MomentCard
                  key={m.moment_id}
                  moment={m}
                  index={i}
                  selected={selectedId === m.moment_id}
                  onSelect={handleSelect}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No moments yet"
              description="Moments appear as the daemon processes events."
            />
          )}
        </div>
      </div>

      {/* Dither overlay + slide-in panel */}
      {selectedId && (
        <>
          {/* Dither backdrop */}
          <div
            className="dither-overlay anim-fade-in fixed inset-0 z-40 cursor-pointer"
            onClick={handleClose}
          />
          {/* Panel */}
          <div className="fixed inset-y-0 right-0 z-50">
            <MomentPanel momentId={selectedId} onClose={handleClose} />
          </div>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span
        className={`font-bold tabular-nums ${accent ? "text-accent" : "text-text-0"}`}
      >
        {numberFormat(value)}
      </span>
      <span className="text-[8px] uppercase tracking-[0.2em] text-text-3">
        {label}
      </span>
    </div>
  );
}

function FilterBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded px-2 py-0.5 text-[9px] font-medium uppercase tracking-[0.15em] transition-colors ${
        active
          ? "bg-accent text-void-0"
          : "text-text-3 hover:text-text-1"
      }`}
    >
      {children}
    </button>
  );
}
