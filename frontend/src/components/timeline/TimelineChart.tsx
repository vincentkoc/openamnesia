import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TimelineBucket } from "../../lib/api";

interface TimelineChartProps {
  data: TimelineBucket[];
}

interface AggBucket {
  bucket: string;
  label: string;
  [source: string]: string | number;
}

const SOURCE_COLORS: Record<string, string> = {
  imessage: "#34D399",
  cursor: "#60A5FA",
  codex: "#F472B6",
  terminal: "#FBBF24",
  slack: "#A78BFA",
  discord: "#818CF8",
  _other: "#9B978E",
};

export function TimelineChart({ data }: TimelineChartProps) {
  // Aggregate by bucket, one key per source
  const sources = [...new Set(data.map((d) => d.source))];
  const bucketMap = new Map<string, AggBucket>();

  for (const item of data) {
    if (!bucketMap.has(item.bucket)) {
      const label = formatBucketLabel(item.bucket);
      bucketMap.set(item.bucket, { bucket: item.bucket, label });
    }
    const entry = bucketMap.get(item.bucket)!;
    entry[item.source] = (entry[item.source] as number ?? 0) + item.event_count;
  }

  const chartData = [...bucketMap.values()].sort((a, b) =>
    a.bucket.localeCompare(b.bucket),
  );

  if (chartData.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center text-[13px] text-ink-50">
        No timeline data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} barGap={0} barCategoryGap="20%">
        <CartesianGrid strokeDasharray="3 3" stroke="#E0DED8" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "#71706E" }}
          tickLine={false}
          axisLine={{ stroke: "#D5D3CC" }}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "#71706E" }}
          tickLine={false}
          axisLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#FAF9F6",
            border: "1px solid #D5D3CC",
            borderRadius: 8,
            fontSize: 12,
            boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
          }}
        />
        {sources.map((source) => (
          <Bar
            key={source}
            dataKey={source}
            stackId="a"
            fill={SOURCE_COLORS[source] ?? SOURCE_COLORS._other}
            radius={sources.indexOf(source) === sources.length - 1 ? [3, 3, 0, 0] : undefined}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function formatBucketLabel(bucket: string): string {
  // "2026-02-06T14:00:00" -> "2pm"
  // "2026-02-06" -> "Feb 6"
  // "2026-06" -> "2026-W06"
  if (bucket.includes("T")) {
    const d = new Date(bucket);
    return d.toLocaleTimeString("en-US", { hour: "numeric" });
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(bucket)) {
    const d = new Date(bucket + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  return bucket;
}
