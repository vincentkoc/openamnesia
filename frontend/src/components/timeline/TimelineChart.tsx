import { useMemo, useState } from "react";
import type { TimelineBucket } from "../../lib/api";
import { cn } from "../../lib/utils";

const SRC_COLORS: Record<string, string> = {
  cursor: "#5B9EFF",
  codex: "#FF6BC1",
  terminal: "#FFD93D",
  imessage: "#3DDC84",
  slack: "#B794F6",
  discord: "#7B8CFF",
  claude: "#FF8C42",
};

const SRC_ORDER = ["cursor", "codex", "terminal", "imessage", "slack", "discord", "claude"];

interface Props {
  data: TimelineBucket[];
  granularity?: "hour" | "day" | "week" | "month";
}

export function TimelineChart({ data, granularity = "hour" }: Props) {
  const [dayOffset, setDayOffset] = useState(0);
  const [hoveredHour, setHoveredHour] = useState<number | null>(null);

  // How many days to show in the tab window
  const WINDOW_SIZE = 5;

  const { days, bars, sessionBars, maxTotal, maxSession, sources, nowHour, windowStart } = useMemo(() => {
    const dayMap = new Map<string, Map<number, { events: Record<string, number>; sessions: number }>>();
    const srcSet = new Set<string>();

    for (const item of data) {
      const date = item.bucket.slice(0, 10);
      const hour = parseInt(item.bucket.slice(11, 13), 10);
      srcSet.add(item.source);
      if (!dayMap.has(date)) dayMap.set(date, new Map());
      const hmap = dayMap.get(date)!;
      if (!hmap.has(hour)) hmap.set(hour, { events: {}, sessions: 0 });
      const h = hmap.get(hour)!;
      h.events[item.source] = (h.events[item.source] ?? 0) + item.event_count;
      h.sessions += item.session_count;
    }

    const days = [...dayMap.keys()].sort().reverse();
    const windowStart = Math.min(dayOffset, Math.max(0, days.length - WINDOW_SIZE));
    const selectedDate = days[dayOffset] ?? days[0] ?? "";
    const hmap = dayMap.get(selectedDate) ?? new Map();

    let maxTotal = 0;
    let maxSession = 0;
    const bars = Array.from({ length: 24 }, (_, h) => {
      const entry = hmap.get(h) ?? { events: {}, sessions: 0 };
      const total = Object.values(entry.events).reduce((a, b) => a + b, 0);
      if (total > maxTotal) maxTotal = total;
      if (entry.sessions > maxSession) maxSession = entry.sessions;
      return { hour: h, total, sources: entry.events, sessions: entry.sessions };
    });

    const sessionBars = bars.map((b) => ({ hour: b.hour, sessions: b.sessions }));

    const now = new Date();
    const todayStr = now.toISOString().slice(0, 10);
    const nowHour = selectedDate === todayStr ? now.getHours() : -1;
    const orderedSources = SRC_ORDER.filter((s) => srcSet.has(s));

    return { days, bars, sessionBars, maxTotal, maxSession, sources: orderedSources, nowHour, windowStart };
  }, [data, dayOffset]);

  if (!data.length) {
    return (
      <div className="flex h-[120px] items-center justify-center font-sans text-[10px] uppercase tracking-widest text-text-3">
        awaiting trace data&hellip;
      </div>
    );
  }

  const W = 1200;
  const BAR_AREA = 100;
  const VOL_AREA = 24;
  const GAP = 4;
  const RULER_Y = BAR_AREA + GAP + VOL_AREA + 4;
  const H = RULER_Y + 24;
  const barW = W / 24;
  const innerW = barW - 3;

  const canGoBack = dayOffset < days.length - 1;
  const canGoForward = dayOffset > 0;

  return (
    <div className="relative">
      {/* Arrow navigation + day tabs + source legend */}
      <div className="flex items-center gap-1 px-4 py-1.5 text-[9px]">
        {/* Arrow nav */}
        <button
          onClick={() => canGoBack && setDayOffset((d) => Math.min(d + WINDOW_SIZE, days.length - 1))}
          disabled={!canGoBack}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoBack ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &laquo;
        </button>
        <button
          onClick={() => canGoBack && setDayOffset((d) => Math.min(d + 1, days.length - 1))}
          disabled={!canGoBack}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoBack ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &lsaquo;
        </button>

        {/* Day tabs window */}
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
          onClick={() => canGoForward && setDayOffset((d) => Math.max(d - 1, 0))}
          disabled={!canGoForward}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoForward ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &rsaquo;
        </button>
        <button
          onClick={() => canGoForward && setDayOffset(0)}
          disabled={!canGoForward}
          className={cn("rounded px-1 py-0.5 font-mono font-bold transition-colors", canGoForward ? "text-text-2 hover:text-text-0" : "text-text-3/30")}
        >
          &raquo;
        </button>

        {/* Source legend */}
        <div className="ml-auto flex items-center gap-3">
          {sources.map((s) => (
            <div key={s} className="flex items-center gap-1 font-sans">
              <div
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: SRC_COLORS[s] ?? "#6B6560" }}
              />
              <span className="uppercase tracking-wider text-text-3">{s}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG chart */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ height: `${H * 0.12}vw`, maxHeight: "150px", minHeight: "90px" }}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="synth-grad" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#1e1b4b" />
            <stop offset="12.5%" stopColor="#4c1d95" />
            <stop offset="25%" stopColor="#d97706" />
            <stop offset="37.5%" stopColor="#f97316" />
            <stop offset="50%" stopColor="#dc2626" />
            <stop offset="62.5%" stopColor="#f97316" />
            <stop offset="75%" stopColor="#7c3aed" />
            <stop offset="87.5%" stopColor="#3730a3" />
            <stop offset="100%" stopColor="#1e1b4b" />
          </linearGradient>
        </defs>

        {/* Subtle grid lines */}
        {[0.25, 0.5, 0.75].map((pct) => (
          <line
            key={pct}
            x1={0}
            y1={BAR_AREA * (1 - pct)}
            x2={W}
            y2={BAR_AREA * (1 - pct)}
            stroke="var(--line-c)"
            strokeWidth="0.5"
            strokeDasharray="2 8"
            opacity="0.25"
          />
        ))}

        {/* Stacked bars (event volume) */}
        {bars.map((bar) => {
          const x = bar.hour * barW + 1.5;
          const totalH = maxTotal > 0 ? (bar.total / maxTotal) * (BAR_AREA - 6) : 0;
          const isHovered = hoveredHour === bar.hour;

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
            <g key={bar.hour}>
              <rect
                x={bar.hour * barW}
                y={0}
                width={barW}
                height={BAR_AREA}
                fill="transparent"
                onMouseEnter={() => setHoveredHour(bar.hour)}
                onMouseLeave={() => setHoveredHour(null)}
              />
              {segments.map((seg) => (
                <rect
                  key={seg.src}
                  x={x}
                  y={seg.y}
                  width={innerW}
                  height={seg.h}
                  fill={seg.color}
                  opacity={isHovered ? 1 : 0.75}
                  rx={1.5}
                  style={{ transition: "opacity 0.15s" }}
                />
              ))}
              {isHovered && bar.total > 0 && (
                <text
                  x={x + innerW / 2}
                  y={stackY - 4}
                  fill="var(--t1)"
                  fontSize="8"
                  textAnchor="middle"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {bar.total}
                </text>
              )}
            </g>
          );
        })}

        {/* Session volume sub-chart (below main bars) */}
        {sessionBars.map((bar) => {
          const x = bar.hour * barW + 1.5;
          const volY = BAR_AREA + GAP;
          const barH = maxSession > 0 ? (bar.sessions / maxSession) * VOL_AREA : 0;
          const isHovered = hoveredHour === bar.hour;

          return (
            <rect
              key={bar.hour}
              x={x}
              y={volY + VOL_AREA - barH}
              width={innerW}
              height={barH}
              fill="var(--color-accent)"
              opacity={isHovered ? 0.5 : 0.2}
              rx={1}
              style={{ transition: "opacity 0.15s" }}
            />
          );
        })}

        {/* Separator line between event bars and session volume */}
        <line
          x1={0}
          y1={BAR_AREA + GAP / 2}
          x2={W}
          y2={BAR_AREA + GAP / 2}
          stroke="var(--line-c)"
          strokeWidth="0.5"
          opacity="0.2"
        />

        {/* Synesthesia time ruler */}
        <rect
          x={0}
          y={RULER_Y}
          width={W}
          height={3}
          fill="url(#synth-grad)"
          opacity="0.45"
          rx={1.5}
        />

        {/* Now marker */}
        {nowHour >= 0 && (
          <g>
            <line
              x1={nowHour * barW + barW / 2}
              y1={0}
              x2={nowHour * barW + barW / 2}
              y2={BAR_AREA + GAP + VOL_AREA}
              stroke="#E8562A"
              strokeWidth="1"
              strokeDasharray="3 5"
              opacity="0.4"
            />
            <circle
              cx={nowHour * barW + barW / 2}
              cy={RULER_Y + 1.5}
              r={4}
              fill="#E8562A"
              opacity="0.9"
            >
              <animate
                attributeName="r"
                values="3;5;3"
                dur="2s"
                repeatCount="indefinite"
              />
            </circle>
          </g>
        )}

        {/* Hour labels */}
        {Array.from({ length: 24 }, (_, h) => h)
          .filter((h) => h % 3 === 0)
          .map((h) => (
            <text
              key={h}
              x={h * barW + barW / 2}
              y={H - 2}
              fill="var(--t2)"
              fontSize="8"
              textAnchor="middle"
              fontFamily="JetBrains Mono, monospace"
              opacity="0.7"
            >
              {String(h).padStart(2, "0")}
            </text>
          ))}
      </svg>
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
