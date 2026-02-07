import { useMemo, useState, useRef, useEffect } from "react";
import type { TimelineBucket } from "../../lib/api";
import { cn } from "../../lib/utils";

const SRC_COLORS: Record<string, string> = {
  cursor: "var(--color-src-cursor)",
  codex: "var(--color-src-codex)",
  terminal: "var(--color-src-terminal)",
  imessage: "var(--color-src-imessage)",
  slack: "var(--color-src-slack)",
  discord: "var(--color-src-discord)",
  claude: "var(--color-src-claude)",
};

const SRC_ORDER = ["cursor", "codex", "terminal", "imessage", "slack", "discord", "claude"];

export type Granularity = "5min" | "10min" | "15min" | "30min" | "hour" | "6hour" | "day";

interface Props {
  data: TimelineBucket[];
  granularity?: Granularity;
}

function barsPerDay(g: Granularity): number {
  switch (g) {
    case "5min": return 288;
    case "10min": return 144;
    case "15min": return 96;
    case "30min": return 48;
    case "hour": return 24;
    case "6hour": return 4;
    case "day": return 1;
  }
}

export function TimelineChart({ data, granularity = "hour" }: Props) {
  const [dayOffset, setDayOffset] = useState(0);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerW, setContainerW] = useState(800);

  const WINDOW_SIZE = 5;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerW(entry.contentRect.width);
      }
    });
    ro.observe(el);
    setContainerW(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  // Reset day offset when granularity changes
  useEffect(() => {
    setDayOffset(0);
  }, [granularity]);

  const { days, bars, sessionBars, maxTotal, maxSession, sources, nowIdx, windowStart } = useMemo(() => {
    const dayMap = new Map<string, Map<number, { events: Record<string, number>; sessions: number }>>();
    const srcSet = new Set<string>();

    for (const item of data) {
      const date = item.bucket.slice(0, 10);
      const hour = parseInt(item.bucket.slice(11, 13), 10);
      const min = parseInt(item.bucket.slice(14, 16), 10);
      srcSet.add(item.source);
      if (!dayMap.has(date)) dayMap.set(date, new Map());
      const hmap = dayMap.get(date)!;

      let bucketIdx: number;
      const bpd = barsPerDay(granularity);
      if (granularity === "day") {
        bucketIdx = 0;
      } else if (granularity === "6hour") {
        bucketIdx = Math.floor(hour / 6);
      } else if (granularity === "hour") {
        bucketIdx = hour;
      } else {
        const minsPerBucket = granularity === "5min" ? 5 : granularity === "10min" ? 10 : granularity === "15min" ? 15 : 30;
        bucketIdx = Math.min(Math.floor((hour * 60 + min) / minsPerBucket), bpd - 1);
      }

      if (!hmap.has(bucketIdx)) hmap.set(bucketIdx, { events: {}, sessions: 0 });
      const h = hmap.get(bucketIdx)!;
      h.events[item.source] = (h.events[item.source] ?? 0) + item.event_count;
      h.sessions += item.session_count;
    }

    const days = [...dayMap.keys()].sort().reverse();
    const windowStart = Math.min(dayOffset, Math.max(0, days.length - WINDOW_SIZE));
    const selectedDate = days[dayOffset] ?? days[0] ?? "";
    const hmap = dayMap.get(selectedDate) ?? new Map();
    const bpd = barsPerDay(granularity);

    let maxTotal = 0;
    let maxSession = 0;
    const bars = Array.from({ length: bpd }, (_, idx) => {
      const entry = hmap.get(idx) ?? { events: {}, sessions: 0 };
      const total = Object.values(entry.events).reduce((a, b) => a + b, 0);
      if (total > maxTotal) maxTotal = total;
      if (entry.sessions > maxSession) maxSession = entry.sessions;
      return { idx, total, sources: entry.events, sessions: entry.sessions };
    });

    const sessionBars = bars.map((b) => ({ idx: b.idx, sessions: b.sessions }));

    const now = new Date();
    const todayStr = now.toISOString().slice(0, 10);
    let nowIdx = -1;
    if (selectedDate === todayStr) {
      const minsPerBucket = granularity === "5min" ? 5 : granularity === "10min" ? 10 : granularity === "15min" ? 15 : granularity === "30min" ? 30 : granularity === "hour" ? 60 : granularity === "6hour" ? 360 : 1440;
      nowIdx = Math.floor((now.getHours() * 60 + now.getMinutes()) / minsPerBucket);
    }
    const orderedSources = SRC_ORDER.filter((s) => srcSet.has(s));

    return { days, bars, sessionBars, maxTotal, maxSession, sources: orderedSources, nowIdx, windowStart };
  }, [data, dayOffset, granularity]);

  if (!data.length) {
    return (
      <div className="flex h-[100px] items-center justify-center font-sans text-[10px] uppercase tracking-widest text-text-3">
        awaiting trace data&hellip;
      </div>
    );
  }

  const bpd = barsPerDay(granularity);
  // Fixed heights
  const BAR_AREA = 80;
  const VOL_AREA = 18;
  const GAP = 3;
  const LABEL_H = 16;
  const H = BAR_AREA + GAP + VOL_AREA + GAP + LABEL_H;

  // Always fill the container width exactly — granularity = zoom level
  const W = containerW;
  const CELL = W / bpd;
  const BAR_W = Math.max(CELL - 2, 1);

  // Label frequency
  const labelEvery = granularity === "5min" ? 12 : granularity === "10min" ? 6 : granularity === "15min" ? 4 : granularity === "30min" ? 2 : granularity === "hour" ? 3 : granularity === "6hour" ? 1 : 1;

  const canGoNewer = dayOffset > 0;
  const canGoOlder = dayOffset < days.length - 1;

  return (
    <div className="relative">
      {/* Arrow navigation + day tabs */}
      <div className="flex items-center gap-1 px-4 py-1.5 text-[9px]">
        <button
          onClick={() => canGoNewer && setDayOffset(0)}
          disabled={!canGoNewer}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoNewer ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &laquo;
        </button>
        <button
          onClick={() => canGoNewer && setDayOffset((d) => Math.max(d - 1, 0))}
          disabled={!canGoNewer}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoNewer ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &lsaquo;
        </button>

        {days.slice(windowStart, windowStart + WINDOW_SIZE).map((day) => {
          const idx = days.indexOf(day);
          return (
            <button
              key={day}
              onClick={() => setDayOffset(idx)}
              className={cn(
                "rounded px-2 py-0.5 font-sans font-medium uppercase tracking-[0.1em] transition-colors",
                idx === dayOffset
                  ? "bg-accent text-void-0"
                  : "text-text-3 hover:text-text-1",
              )}
            >
              {dayLabel(day, idx)}
            </button>
          );
        })}

        <button
          onClick={() => canGoOlder && setDayOffset((d) => Math.min(d + 1, days.length - 1))}
          disabled={!canGoOlder}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoOlder ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &rsaquo;
        </button>
        <button
          onClick={() => canGoOlder && setDayOffset(days.length - 1)}
          disabled={!canGoOlder}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoOlder ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &raquo;
        </button>
      </div>

      {/* SVG chart — always full width, scrolls only when bars overflow */}
      <div ref={containerRef} className="w-full overflow-x-auto pb-1">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          height={H}
          className="block"
          style={{ minWidth: W }}
        >
          {/* Grid lines */}
          {[0.25, 0.5, 0.75].map((pct) => (
            <line
              key={pct}
              x1={0} y1={BAR_AREA * (1 - pct)} x2={W} y2={BAR_AREA * (1 - pct)}
              stroke="var(--line-c)" strokeWidth="0.5" strokeDasharray="2 6" opacity="0.2"
            />
          ))}

          {/* Stacked bars */}
          {bars.map((bar) => {
            const x = bar.idx * CELL + (CELL - BAR_W) / 2;
            const totalH = maxTotal > 0 ? (bar.total / maxTotal) * (BAR_AREA - 4) : 0;
            const isHovered = hoveredIdx === bar.idx;

            let stackY = BAR_AREA;
            const segments: { src: string; y: number; h: number; color: string }[] = [];
            for (const src of sources) {
              const count = bar.sources[src] ?? 0;
              if (count === 0) continue;
              const segH = (count / bar.total) * totalH;
              stackY -= segH;
              segments.push({ src, y: stackY, h: segH, color: SRC_COLORS[src] ?? "#6B6560" });
            }

            return (
              <g key={bar.idx}>
                <rect
                  x={bar.idx * CELL} y={0} width={CELL} height={BAR_AREA}
                  fill="transparent"
                  onMouseEnter={() => setHoveredIdx(bar.idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                />
                {segments.map((seg) => (
                  <rect
                    key={seg.src}
                    x={x} y={seg.y} width={BAR_W} height={seg.h}
                    fill={seg.color} opacity={isHovered ? 1 : 0.7} rx={1}
                    style={{ transition: "opacity 0.15s" }}
                  />
                ))}
                {isHovered && bar.total > 0 && (
                  <text
                    x={x + BAR_W / 2} y={stackY - 3}
                    fill="var(--t0)" fontSize="7" textAnchor="middle"
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {bar.total}
                  </text>
                )}
              </g>
            );
          })}

          {/* Session volume sub-chart */}
          {sessionBars.map((bar) => {
            const x = bar.idx * CELL + (CELL - BAR_W) / 2;
            const volY = BAR_AREA + GAP;
            const barH = maxSession > 0 ? (bar.sessions / maxSession) * VOL_AREA : 0;
            const isHovered = hoveredIdx === bar.idx;

            return (
              <rect
                key={bar.idx}
                x={x} y={volY + VOL_AREA - barH} width={BAR_W} height={barH}
                fill="var(--color-accent)" opacity={isHovered ? 0.5 : 0.2} rx={1}
                style={{ transition: "opacity 0.15s" }}
              />
            );
          })}

          {/* Separator */}
          <line
            x1={0} y1={BAR_AREA + GAP / 2} x2={W} y2={BAR_AREA + GAP / 2}
            stroke="var(--line-c)" strokeWidth="0.5" opacity="0.15"
          />

          {/* Now marker */}
          {nowIdx >= 0 && nowIdx < bpd && (
            <g>
              <line
                x1={nowIdx * CELL + CELL / 2} y1={0}
                x2={nowIdx * CELL + CELL / 2} y2={BAR_AREA + GAP + VOL_AREA}
                stroke="var(--color-accent)" strokeWidth="1" strokeDasharray="2 4" opacity="0.5"
              />
              <circle
                cx={nowIdx * CELL + CELL / 2} cy={BAR_AREA + GAP + VOL_AREA + 2}
                r={2.5} fill="var(--color-accent)" opacity="0.9"
              >
                <animate attributeName="r" values="2;3.5;2" dur="2s" repeatCount="indefinite" />
              </circle>
            </g>
          )}

          {/* Time labels */}
          {Array.from({ length: bpd }, (_, i) => i)
            .filter((i) => i % labelEvery === 0)
            .map((i) => {
              let label: string;
              if (granularity === "day") {
                label = "all";
              } else if (granularity === "6hour") {
                label = String(i * 6).padStart(2, "0");
              } else if (granularity === "hour") {
                label = String(i).padStart(2, "0");
              } else {
                const minsPerBucket = granularity === "5min" ? 5 : granularity === "10min" ? 10 : granularity === "15min" ? 15 : 30;
                const totalMins = i * minsPerBucket;
                const hh = Math.floor(totalMins / 60);
                const mm = totalMins % 60;
                label = `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
              }
              return (
                <text
                  key={i}
                  x={i * CELL + CELL / 2} y={H - 3}
                  fill="var(--t2)" fontSize={CELL < 8 ? "4" : CELL < 14 ? "5" : "7"} textAnchor="middle"
                  fontFamily="JetBrains Mono, monospace" opacity="0.6"
                >
                  {label}
                </text>
              );
            })}
        </svg>
      </div>
    </div>
  );
}

function dayLabel(iso: string, offset: number): string {
  if (offset === 0) return "today";
  if (offset === 1) return "yesterday";
  const d = new Date(iso + "T00:00:00");
  return (
    d.toLocaleDateString("en-US", { weekday: "short" }).toLowerCase() +
    " " +
    d.getDate()
  );
}
