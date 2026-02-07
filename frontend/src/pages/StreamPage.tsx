import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { cn, sourceColor } from "../lib/utils";
import { TimelineChart } from "../components/timeline/TimelineChart";
import type { Granularity } from "../components/timeline/TimelineChart";
import { MomentCard } from "../components/timeline/MomentCard";
import { MomentPanel } from "../components/timeline/MomentPanel";
import { EventTickerRow } from "../components/timeline/EventTickerRow";
import { EmptyState } from "../components/common/EmptyState";
import { IconGrid, IconList } from "../components/common/Icons";
import { useTableFilter, FilterInput, useResizableColumns } from "../lib/hooks";
import { useState, useCallback, useMemo } from "react";

type ViewMode = "refined" | "raw";
type LayoutMode = "compact" | "cards";

const GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: "5min", label: "5m" },
  { value: "10min", label: "10m" },
  { value: "15min", label: "15m" },
  { value: "30min", label: "30m" },
  { value: "hour", label: "1h" },
  { value: "6hour", label: "6h" },
  { value: "day", label: "1d" },
];

const MOMENT_COLS = [
  { key: "time", initialWidth: 80, minWidth: 50 },
  { key: "source", initialWidth: 60, minWidth: 40 },
  { key: "intent", initialWidth: 0 },
  { key: "outcome", initialWidth: 200, minWidth: 100 },
  { key: "turns", initialWidth: 80, minWidth: 50 },
  { key: "friction", initialWidth: 60, minWidth: 40 },
  { key: "session", initialWidth: 80, minWidth: 50 },
];

const EVENT_COLS = [
  { key: "time", initialWidth: 80, minWidth: 50 },
  { key: "source", initialWidth: 60, minWidth: 40 },
  { key: "actor", initialWidth: 50, minWidth: 35 },
  { key: "content", initialWidth: 0 },
  { key: "tool", initialWidth: 80, minWidth: 50 },
  { key: "status", initialWidth: 60, minWidth: 40 },
];

export function StreamPage() {
  const [src, setSrc] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("refined");
  const [granularity, setGranularity] = useState<Granularity>("10min");
  const [layout, setLayout] = useState<LayoutMode>("compact");

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
  const uniqueSources = useMemo(() => {
    const seen = new Set<string>();
    return sources.filter((s) => {
      if (seen.has(s.source)) return false;
      seen.add(s.source);
      return true;
    });
  }, [sources]);

  const { filteredItems: filteredMoments, query: momentQuery, setQuery: setMomentQuery } = useTableFilter({
    items: moments?.items ?? [],
    searchFields: ["intent", "outcome", "source", "summary"],
  });
  const { filteredItems: filteredEvents, query: eventQuery, setQuery: setEventQuery } = useTableFilter({
    items: events?.items ?? [],
    searchFields: ["content", "source", "actor", "tool_name"],
  });

  const momentCols = useResizableColumns(MOMENT_COLS);
  const eventCols = useResizableColumns(EVENT_COLS);

  const handleSelect = useCallback((id: string) => {
    if (viewMode === "refined") {
      setSelectedId((prev) => (prev === id ? null : id));
    }
  }, [viewMode]);

  const handleClose = useCallback(() => setSelectedId(null), []);

  return (
    <div className="flex h-full">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Control bar */}
        <div className="flex shrink-0 items-center gap-3 border-b border-line/30 px-4 py-1.5">
          <div className="toggle-group">
            <button className={viewMode === "refined" ? "active" : ""} onClick={() => { setViewMode("refined"); setSelectedId(null); }}>refined</button>
            <button className={viewMode === "raw" ? "active" : ""} onClick={() => { setViewMode("raw"); setSelectedId(null); }}>raw</button>
          </div>

          <div className="toggle-group">
            {GRANULARITIES.map((g) => (
              <button key={g.value} className={granularity === g.value ? "active" : ""} onClick={() => setGranularity(g.value)}>{g.label}</button>
            ))}
          </div>

          <FilterInput
            value={viewMode === "refined" ? momentQuery : eventQuery}
            onChange={viewMode === "refined" ? setMomentQuery : setEventQuery}
            placeholder="filter..."
          />

          {viewMode === "refined" && (
            <div className="toggle-group">
              <button className={layout === "compact" ? "active" : ""} onClick={() => setLayout("compact")}>
                <IconList size={11} className="mr-0.5 inline" />list
              </button>
              <button className={layout === "cards" ? "active" : ""} onClick={() => setLayout("cards")}>
                <IconGrid size={11} className="mr-0.5 inline" />grid
              </button>
            </div>
          )}

          <div className="ml-auto flex items-center gap-1.5">
            <FilterChip active={!src} onClick={() => setSrc("")}>all</FilterChip>
            {uniqueSources.map((s) => (
              <FilterChip key={s.source} active={src === s.source} onClick={() => setSrc(s.source === src ? "" : s.source)} source={s.source}>
                {s.source}
              </FilterChip>
            ))}
            <span className="ml-2 font-mono text-[9px] tabular-nums tracking-wider text-text-3">
              {viewMode === "refined" ? `${filteredMoments.length} moments` : `${filteredEvents.length} events`}
            </span>
          </div>
        </div>

        {/* Volume chart */}
        <div className="shrink-0 border-b border-line/30">
          <TimelineChart data={tl?.items ?? []} granularity={granularity} />
        </div>

        {/* Column headers (compact only) */}
        {layout === "compact" && viewMode === "refined" && (
          <div className="section-rule gap-0">
            {[
              { key: "time", label: "time" },
              { key: "source", label: "source" },
              { key: "intent", label: "intent", flex: true },
              { key: "outcome", label: "outcome" },
              { key: "turns", label: "turns", right: true },
              { key: "friction", label: "friction", right: true },
              { key: "session", label: "session", right: true },
            ].map((col) => (
              <span
                key={col.key}
                className={cn("relative shrink-0", col.flex && "min-w-0 flex-1", col.right && "text-right")}
                style={!col.flex && momentCols.widths[col.key] ? { width: momentCols.widths[col.key], flexShrink: 0 } : undefined}
              >
                {col.label}
                {!col.flex && <div {...momentCols.getResizeHandleProps(col.key)} />}
              </span>
            ))}
          </div>
        )}
        {layout === "compact" && viewMode === "raw" && (
          <div className="section-rule gap-0">
            {[
              { key: "time", label: "time" },
              { key: "source", label: "source" },
              { key: "actor", label: "actor" },
              { key: "content", label: "content", flex: true },
              { key: "tool", label: "tool" },
              { key: "status", label: "status", right: true },
            ].map((col) => (
              <span
                key={col.key}
                className={cn("relative shrink-0", col.flex && "min-w-0 flex-1", col.right && "text-right")}
                style={!col.flex && eventCols.widths[col.key] ? { width: eventCols.widths[col.key], flexShrink: 0 } : undefined}
              >
                {col.label}
                {!col.flex && <div {...eventCols.getResizeHandleProps(col.key)} />}
              </span>
            ))}
          </div>
        )}

        {/* Data rows */}
        <div className="relative min-h-0 flex-1 overflow-y-auto">
          {viewMode === "refined" ? (
            filteredMoments.length > 0 ? (
              layout === "cards" ? (
                <div className="grid grid-cols-2 gap-3 p-4 xl:grid-cols-3">
                  {filteredMoments.map((m, i) => (
                    <MomentCard key={m.moment_id} moment={m} index={i} variant="card" selected={selectedId === m.moment_id} onSelect={handleSelect} />
                  ))}
                </div>
              ) : (
                <div>
                  {filteredMoments.map((m, i) => (
                    <MomentCard key={m.moment_id} moment={m} index={i} variant="row" selected={selectedId === m.moment_id} onSelect={handleSelect} columnWidths={momentCols.widths} />
                  ))}
                </div>
              )
            ) : (
              <EmptyState title="No moments yet" description="Moments appear as the daemon processes events." icon="moments" />
            )
          ) : (
            filteredEvents.length > 0 ? (
              <div>
                {filteredEvents.map((e) => (
                  <EventTickerRow key={e.event_id} event={e} columnWidths={eventCols.widths} />
                ))}
              </div>
            ) : (
              <EmptyState title="No events yet" description="Events appear as sources send data." icon="events" />
            )
          )}
        </div>
      </div>

      {/* Panel */}
      {selectedId && viewMode === "refined" && (
        <>
          <div className="dither-overlay anim-fade-in fixed inset-0 z-40 cursor-pointer" onClick={handleClose} />
          <div className="fixed inset-y-0 right-0 z-50">
            <MomentPanel momentId={selectedId} onClose={handleClose} />
          </div>
        </>
      )}
    </div>
  );
}

function FilterChip({ active, onClick, children, source }: {
  active: boolean; onClick: () => void; children: React.ReactNode; source?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded px-2 py-0.5 font-sans text-[9px] font-medium uppercase tracking-[0.1em] transition-colors",
        active ? "bg-accent text-void-0" : "text-text-3 hover:text-text-1 hover:bg-void-2",
      )}
    >
      {source && <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(source))} />}
      {children}
    </button>
  );
}
