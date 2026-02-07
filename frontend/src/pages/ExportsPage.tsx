import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { cn, formatDate, formatTime, sourceColor, truncate, timeAgo } from "../lib/utils";
import { EmptyState } from "../components/common/EmptyState";
import { IconChevronDown, IconChevronRight } from "../components/common/Icons";
import { useState, useMemo } from "react";

type Period = "daily" | "weekly" | "monthly";

const PERIODS: Period[] = ["daily", "weekly", "monthly"];

interface DayGroup {
  date: string;
  label: string;
  moments: { moment_id: string; source?: string; intent?: string; outcome?: string; summary?: string; session_start_ts?: string; friction_score: number | null }[];
}

export function ExportsPage() {
  const [period, setPeriod] = useState<Period>("daily");
  const [expandedDay, setExpandedDay] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const { data: moments } = useQuery({
    queryKey: ["moments"],
    queryFn: () => api.moments({ limit: 200 }),
  });

  const { data: skills } = useQuery({
    queryKey: ["skills"],
    queryFn: () => api.skills({ limit: 50 }),
  });

  // Group moments by date
  const groups: DayGroup[] = useMemo(() => {
    if (!moments?.items) return [];
    const map = new Map<string, DayGroup>();

    for (const m of moments.items) {
      const ts = m.session_start_ts ?? m.session_end_ts;
      if (!ts) continue;
      const d = new Date(ts);

      let key: string;
      let label: string;

      if (period === "daily") {
        key = ts.slice(0, 10);
        label = formatDate(ts);
      } else if (period === "weekly") {
        // ISO week start (Monday)
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1);
        const monday = new Date(d);
        monday.setDate(diff);
        key = `week-${monday.toISOString().slice(0, 10)}`;
        label = `Week of ${formatDate(monday.toISOString())}`;
      } else {
        key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
        label = d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
      }

      if (!map.has(key)) map.set(key, { date: key, label, moments: [] });
      map.get(key)!.moments.push(m);
    }

    return [...map.values()].sort((a, b) => b.date.localeCompare(a.date));
  }, [moments, period]);

  // Generate markdown for a group
  function generateMarkdown(group: DayGroup): string {
    const lines: string[] = [];
    lines.push(`# ${group.label}`);
    lines.push("");
    lines.push(`> ${group.moments.length} moments recorded`);
    lines.push("");

    for (const m of group.moments) {
      const time = m.session_start_ts ? formatTime(m.session_start_ts) : "--:--";
      const src = m.source ?? "unknown";
      lines.push(`## ${time} — [${src}] ${m.intent ?? "Untitled"}`);
      lines.push("");
      if (m.summary) {
        lines.push(m.summary);
        lines.push("");
      }
      if (m.outcome) {
        lines.push(`**Outcome:** ${m.outcome}`);
        lines.push("");
      }
      if (m.friction_score !== null && m.friction_score !== undefined) {
        const fl = m.friction_score < 0.1 ? "smooth" : m.friction_score < 0.3 ? "low" : m.friction_score < 0.6 ? "medium" : "high";
        lines.push(`**Friction:** ${fl} (${(m.friction_score * 100).toFixed(0)}%)`);
        lines.push("");
      }
      lines.push("---");
      lines.push("");
    }

    return lines.join("\n");
  }

  // Generate full export markdown
  function generateFullExport(): string {
    const lines: string[] = [];
    lines.push("# OpenAmnesia Export");
    lines.push("");
    lines.push(`Generated: ${new Date().toISOString()}`);
    lines.push(`Period: ${period}`);
    lines.push(`Total moments: ${moments?.items.length ?? 0}`);
    lines.push("");

    if (skills?.items && skills.items.length > 0) {
      lines.push("## Skills");
      lines.push("");
      for (const s of skills.items) {
        const status = s.status === "promoted" ? "built" : s.status;
        const rate = (s.metrics_json?.success_rate as number | undefined);
        lines.push(`- **${s.name}** (v${s.version}) — ${status}${rate !== undefined ? ` — ${(rate * 100).toFixed(0)}% success` : ""}`);
      }
      lines.push("");
    }

    for (const g of groups) {
      lines.push(generateMarkdown(g));
    }

    return lines.join("\n");
  }

  function copyToClipboard(text: string, label: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopyFeedback(label);
      setTimeout(() => setCopyFeedback(null), 2000);
    });
  }

  return (
    <div className="flex h-full flex-col">
      {/* Control bar */}
      <div className="flex shrink-0 items-center gap-3 border-b border-line/30 px-4 py-1.5">
        <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.1em] text-text-0">Exports</span>

        <div className="toggle-group">
          {PERIODS.map((p) => (
            <button key={p} className={period === p ? "active" : ""} onClick={() => setPeriod(p)}>{p}</button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => copyToClipboard(generateFullExport(), "full")}
            className="rounded border border-line/50 bg-void-1 px-2.5 py-1 font-sans text-[9px] font-semibold uppercase tracking-wider text-text-2 transition-colors hover:bg-void-2 hover:text-text-0"
          >
            {copyFeedback === "full" ? "copied!" : "copy all markdown"}
          </button>
          <span className="font-mono text-[9px] tabular-nums text-text-3">{groups.length} {period === "daily" ? "days" : period === "weekly" ? "weeks" : "months"}</span>
        </div>
      </div>

      {/* Config info */}
      <div className="flex shrink-0 items-center gap-4 border-b border-line/20 bg-void-1/30 px-4 py-1.5">
        <div className="flex items-center gap-4 font-mono text-[9px] text-text-3">
          <span>export dir: <span className="text-text-2">./exports/memory</span></span>
          <span>skills dir: <span className="text-text-2">./exports/skills</span></span>
          <span>memory: <span className="text-text-2">openclawd</span></span>
          <span>formats: <span className="text-text-2">md</span></span>
        </div>
      </div>

      {/* Timeline */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {groups.length > 0 ? (
          <div>
            {groups.map((group) => {
              const isExpanded = expandedDay === group.date;
              return (
                <div key={group.date}>
                  {/* Day header */}
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => setExpandedDay(isExpanded ? null : group.date)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setExpandedDay(isExpanded ? null : group.date); } }}
                    className={cn("data-row cursor-pointer", isExpanded && "selected")}
                  >
                    <span className="flex w-[24px] shrink-0 items-center justify-center">
                      {isExpanded ? <IconChevronDown size={12} className="text-text-2" /> : <IconChevronRight size={12} className="text-text-3" />}
                    </span>
                    <span className="font-sans text-[11px] font-semibold text-text-0">{group.label}</span>
                    <span className="ml-auto flex items-center gap-3">
                      {/* Source dots summary */}
                      <span className="flex items-center gap-1">
                        {[...new Set(group.moments.map((m) => m.source).filter(Boolean))].map((src) => (
                          <span key={src} className={cn("h-1.5 w-1.5 rounded-full", sourceColor(src!))} title={src!} />
                        ))}
                      </span>
                      <span className="font-mono text-[10px] tabular-nums text-text-2">{group.moments.length} moments</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); copyToClipboard(generateMarkdown(group), group.date); }}
                        className="rounded border border-line/40 px-1.5 py-0.5 font-sans text-[8px] font-medium uppercase tracking-wider text-text-3 transition-colors hover:bg-void-2 hover:text-text-1"
                      >
                        {copyFeedback === group.date ? "copied!" : "copy md"}
                      </button>
                    </span>
                  </div>

                  {/* Expanded markdown preview */}
                  {isExpanded && (
                    <div className="border-b border-line/20 bg-void-1/30">
                      {group.moments.map((m, i) => (
                        <div key={m.moment_id} className={cn("border-b border-line/10 px-6 py-2.5", i % 2 === 0 && "bg-void-1/20")}>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-[10px] tabular-nums text-text-3">
                              {m.session_start_ts ? formatTime(m.session_start_ts) : "--:--"}
                            </span>
                            {m.source && (
                              <span className="flex items-center gap-1">
                                <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(m.source))} />
                                <span className="font-sans text-[9px] uppercase text-text-3">{m.source}</span>
                              </span>
                            )}
                            {m.friction_score !== null && m.friction_score !== undefined && (
                              <span className={cn(
                                "font-sans text-[8px] font-semibold uppercase",
                                m.friction_score < 0.3 ? "text-ok" : m.friction_score < 0.6 ? "text-warn" : "text-err",
                              )}>
                                {m.friction_score < 0.1 ? "smooth" : m.friction_score < 0.3 ? "low" : m.friction_score < 0.6 ? "medium" : "high"}
                              </span>
                            )}
                          </div>
                          <div className="font-mono text-[11px] font-medium text-text-0 mb-0.5">
                            {m.intent ?? "Untitled moment"}
                          </div>
                          {m.summary && (
                            <div className="font-mono text-[10px] leading-relaxed text-text-2 mb-0.5">
                              {truncate(m.summary, 200)}
                            </div>
                          )}
                          {m.outcome && (
                            <div className="font-mono text-[10px] text-text-1">
                              <span className="text-text-3">outcome:</span> {truncate(m.outcome, 120)}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState title="No exports yet" description="Exports appear as moments are processed. Configure exports in config.yaml." icon="default" />
        )}

        {/* Skills export section */}
        {skills?.items && skills.items.length > 0 && (
          <div className="mt-2">
            <div className="section-rule gap-0">
              <span className="min-w-0 flex-1">skills export preview</span>
            </div>
            {skills.items.map((s) => {
              const displayStatus = s.status === "promoted" ? "built" : s.status;
              const rate = (s.metrics_json?.success_rate as number | undefined);
              return (
                <div key={s.skill_id} className="data-row">
                  <span className="w-[200px] shrink-0 truncate font-medium text-text-0">{s.name}</span>
                  <span className="w-[50px] shrink-0 text-text-3">{s.version}</span>
                  <span className={cn(
                    "w-[80px] shrink-0 text-[10px] font-semibold uppercase",
                    displayStatus === "built" ? "text-ok" : displayStatus === "validated" ? "text-accent" : "text-text-3",
                  )}>
                    {displayStatus}
                  </span>
                  <span className="w-[60px] shrink-0 text-right tabular-nums text-ok">
                    {rate !== undefined ? `${(rate * 100).toFixed(0)}%` : "--"}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[10px] text-text-3">
                    {timeAgo(s.updated_ts)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
