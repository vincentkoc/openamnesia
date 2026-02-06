import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { cn, sourceColor } from "../lib/utils";
import { TimelineChart } from "../components/timeline/TimelineChart";
import { MomentCard } from "../components/timeline/MomentCard";
import { MomentPanel } from "../components/timeline/MomentPanel";
import { EventTickerRow } from "../components/timeline/EventTickerRow";
import { EmptyState } from "../components/common/EmptyState";
import { useState, useCallback, useMemo } from "react";

type ViewMode = "refined" | "raw";
type Granularity = "hour" | "day" | "week" | "month";

export function StreamPage() {
  const [src, setSrc] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("refined");
  const [granularity, setGranularity] = useState<Granularity>("hour");

  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const { data: tl } = useQuery({
    queryKey: ["timeline", granularity],
    queryFn: () => api.timeline({ granularity }),
  });
  const { data: moments } = useQuery({
    queryKey: ["moments", src],
    queryFn: () => api.moments({ source: src || undefined, limit: 50 }),
  });
  const { data: events } = useQuery({
    queryKey: ["events", src],
    queryFn: () => api.events({ source: src || undefined, limit: 100 }),
    enabled: viewMode === "raw",
  });

  const sources = stats?.sources ?? [];

  // Deduplicate sources for filter chips
  const uniqueSources = useMemo(() => {
    const seen = new Set<string>();
    return sources.filter((s) => {
      if (seen.has(s.source)) return false;
      seen.add(s.source);
      return true;
    });
  }, [sources]);

  const handleSelect = useCallback((id: string) => {
    if (viewMode === "refined") {
      setSelectedId((prev) => (prev === id ? null : id));
    }
  }, [viewMode]);

  const handleClose = useCallback(() => {
    setSelectedId(null);
  }, []);

  return (
    <div className="flex h-full">
      {/* Main content area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Control bar */}
        <div className="flex shrink-0 items-center gap-4 border-b border-line/30 px-4 py-1.5">
          {/* Left: Raw/Refined toggle */}
          <div className="toggle-group">
            <button
              className={viewMode === "refined" ? "active" : ""}
              onClick={() => { setViewMode("refined"); setSelectedId(null); }}
            >
              refined
            </button>
            <button
              className={viewMode === "raw" ? "active" : ""}
              onClick={() => { setViewMode("raw"); setSelectedId(null); }}
            >
              raw
            </button>
          </div>

          {/* Center: Granularity selector */}
          <div className="toggle-group">
            {(["hour", "day", "week", "month"] as Granularity[]).map((g) => (
              <button
                key={g}
                className={granularity === g ? "active" : ""}
                onClick={() => setGranularity(g)}
              >
                {g}
              </button>
            ))}
          </div>

          {/* Right: Source filter chips + count */}
          <div className="ml-auto flex items-center gap-1.5">
            <FilterChip active={!src} onClick={() => setSrc("")}>
              all
            </FilterChip>
            {uniqueSources.map((s) => (
              <FilterChip
                key={s.source}
                active={src === s.source}
                onClick={() => setSrc(s.source === src ? "" : s.source)}
                source={s.source}
              >
                {s.source}
              </FilterChip>
            ))}
            <span className="ml-2 font-mono text-[9px] tabular-nums tracking-wider text-text-3">
              {viewMode === "refined"
                ? `${moments?.total ?? 0} moments`
                : `${events?.total ?? 0} events`}
            </span>
          </div>
        </div>

        {/* Volume chart */}
        <div className="shrink-0 border-b border-line/30">
          <TimelineChart data={tl?.items ?? []} granularity={granularity} />
        </div>

        {/* Column headers */}
        {viewMode === "refined" ? (
          <div className="section-rule gap-0">
            <span className="w-[80px] shrink-0">time</span>
            <span className="w-[60px] shrink-0">source</span>
            <span className="min-w-0 flex-1">intent</span>
            <span className="w-[200px] shrink-0">outcome</span>
            <span className="w-[80px] shrink-0 text-right">turns</span>
            <span className="w-[60px] shrink-0 text-right">friction</span>
            <span className="w-[80px] shrink-0 text-right">session</span>
          </div>
        ) : (
          <div className="section-rule gap-0">
            <span className="w-[80px] shrink-0">time</span>
            <span className="w-[60px] shrink-0">source</span>
            <span className="w-[50px] shrink-0">actor</span>
            <span className="min-w-0 flex-1">content</span>
            <span className="w-[80px] shrink-0">tool</span>
            <span className="w-[60px] shrink-0 text-right">status</span>
          </div>
        )}

        {/* Data rows */}
        <div className="relative min-h-0 flex-1 overflow-y-auto">
          {viewMode === "refined" ? (
            moments && moments.items.length > 0 ? (
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
            )
          ) : (
            events && events.items.length > 0 ? (
              <div>
                {events.items.map((e) => (
                  <EventTickerRow key={e.event_id} event={e} />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No events yet"
                description="Events appear as sources send data."
              />
            )
          )}
        </div>
      </div>

      {/* Dither overlay + slide-in panel (refined mode only) */}
      {selectedId && viewMode === "refined" && (
        <>
          <div
            className="dither-overlay anim-fade-in fixed inset-0 z-40 cursor-pointer"
            onClick={handleClose}
          />
          <div className="fixed inset-y-0 right-0 z-50">
            <MomentPanel momentId={selectedId} onClose={handleClose} />
          </div>
        </>
      )}
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
  source,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  source?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded px-2 py-0.5 font-sans text-[9px] font-medium uppercase tracking-[0.1em] transition-colors",
        active
          ? "bg-accent text-void-0"
          : "text-text-3 hover:text-text-1 hover:bg-void-2",
      )}
    >
      {source && (
        <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(source))} />
      )}
      {children}
    </button>
  );
}
