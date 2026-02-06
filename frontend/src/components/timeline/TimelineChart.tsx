import { useMemo } from "react";
import type { TimelineBucket } from "../../lib/api";

interface Props {
  data: TimelineBucket[];
}

const SRC_COLORS: Record<string, string> = {
  cursor: "#5B9EFF",
  codex: "#FF6BC1",
  terminal: "#FFD93D",
  imessage: "#3DDC84",
  slack: "#B794F6",
  discord: "#7B8CFF",
};

const FALLBACK = "#6B6560";

export function TimelineChart({ data }: Props) {
  const { bars, maxTotal, sources } = useMemo(() => {
    const bucketMap = new Map<string, Record<string, number>>();
    const srcSet = new Set<string>();

    for (const item of data) {
      srcSet.add(item.source);
      if (!bucketMap.has(item.bucket)) bucketMap.set(item.bucket, {});
      const b = bucketMap.get(item.bucket)!;
      b[item.source] = (b[item.source] ?? 0) + item.event_count;
    }

    const sorted = [...bucketMap.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    const sources = [...srcSet];
    let maxTotal = 0;
    const bars = sorted.map(([bucket, counts]) => {
      const total = Object.values(counts).reduce((a, b) => a + b, 0);
      if (total > maxTotal) maxTotal = total;
      return { bucket, counts, total };
    });

    return { bars, maxTotal, sources };
  }, [data]);

  if (!bars.length) {
    return (
      <div className="flex h-[120px] items-center justify-center text-[10px] tracking-widest uppercase text-text-3">
        awaiting trace data&hellip;
      </div>
    );
  }

  const W = 1000;
  const H = 120;
  const barW = Math.max(2, Math.min(12, (W - bars.length) / bars.length));
  const gap = Math.max(1, barW * 0.15);
  const totalW = bars.length * (barW + gap);
  const offsetX = (W - totalW) / 2;

  return (
    <div className="relative overflow-hidden">
      {/* Ambient glow behind the chart */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: `radial-gradient(ellipse 60% 100% at 50% 100%, rgba(232,86,42,0.06) 0%, transparent 70%)`,
        }}
      />

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ height: "120px" }}
        preserveAspectRatio="none"
      >
        {/* Baseline */}
        <line x1="0" y1={H - 0.5} x2={W} y2={H - 0.5} stroke="#2A2A38" strokeWidth="0.5" />

        {bars.map((bar, i) => {
          const x = offsetX + i * (barW + gap);
          let y = H;

          return (
            <g key={bar.bucket}>
              {sources.map((src) => {
                const count = bar.counts[src] ?? 0;
                if (count === 0) return null;
                const h = (count / maxTotal) * (H - 4);
                y -= h;
                const color = SRC_COLORS[src] ?? FALLBACK;

                return (
                  <rect
                    key={src}
                    x={x}
                    y={y}
                    width={barW}
                    height={h}
                    fill={color}
                    opacity={0.75}
                    rx={barW > 4 ? 1 : 0}
                  >
                    <animate
                      attributeName="height"
                      from="0"
                      to={h}
                      dur="0.6s"
                      begin={`${i * 15}ms`}
                      fill="freeze"
                      calcMode="spline"
                      keySplines="0.16 1 0.3 1"
                    />
                    <animate
                      attributeName="y"
                      from={H}
                      to={y}
                      dur="0.6s"
                      begin={`${i * 15}ms`}
                      fill="freeze"
                      calcMode="spline"
                      keySplines="0.16 1 0.3 1"
                    />
                  </rect>
                );
              })}
            </g>
          );
        })}

        {/* Peak line */}
        <line x1="0" y1="2" x2={W} y2="2" stroke="#E8562A" strokeWidth="0.3" strokeDasharray="4 8" opacity="0.3" />
      </svg>

      {/* Time labels */}
      <div className="mt-1 flex justify-between px-2 text-[8px] uppercase tracking-[0.15em] text-text-3">
        <span>{fmtLabel(bars[0]?.bucket ?? "")}</span>
        <span>{fmtLabel(bars[Math.floor(bars.length / 2)]?.bucket ?? "")}</span>
        <span>{fmtLabel(bars[bars.length - 1]?.bucket ?? "")}</span>
      </div>

      {/* Source legend */}
      <div className="mt-2 flex items-center justify-center gap-4">
        {sources.map((src) => (
          <div key={src} className="flex items-center gap-1.5">
            <div
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: SRC_COLORS[src] ?? FALLBACK }}
            />
            <span className="text-[8px] uppercase tracking-[0.15em] text-text-3">{src}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function fmtLabel(b: string): string {
  if (!b) return "";
  if (b.includes("T")) {
    const d = new Date(b);
    return d.toLocaleTimeString("en-US", { hour: "numeric", hour12: true }).toLowerCase();
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(b)) {
    return new Date(b + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  return b;
}
