import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { cn, timeAgo } from "../lib/utils";
import { EmptyState } from "../components/common/EmptyState";
import { SkillCard } from "../components/skills/SkillCard";
import { IconGrid, IconList, IconZap, IconPlay, IconX } from "../components/common/Icons";
import { useTableFilter, FilterInput, useResizableColumns } from "../lib/hooks";
import { useState, useCallback } from "react";

const FILTERS = ["all", "candidate", "validated", "built"] as const;
type LayoutMode = "compact" | "cards";

const STATUS_COLOR: Record<string, string> = {
  built: "text-ok",
  validated: "text-accent",
  candidate: "text-text-2",
};

const COLS = [
  { key: "name", initialWidth: 200, minWidth: 120 },
  { key: "version", initialWidth: 60, minWidth: 40 },
  { key: "status", initialWidth: 80, minWidth: 60 },
  { key: "success", initialWidth: 70, minWidth: 50 },
  { key: "avg_turns", initialWidth: 70, minWidth: 50 },
  { key: "seen", initialWidth: 60, minWidth: 40 },
  { key: "triggers", initialWidth: 0 },
  { key: "actions", initialWidth: 120, minWidth: 90 },
  { key: "updated", initialWidth: 80, minWidth: 60 },
];

// Map backend status to display label
function statusLabel(status: string): string {
  if (status === "promoted") return "built";
  return status;
}

export function SkillsPage() {
  const [status, setStatus] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [layout, setLayout] = useState<LayoutMode>("compact");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["skills", status],
    queryFn: () => {
      // Map "built" filter back to "promoted" for the API
      const apiStatus = status === "built" ? "promoted" : status === "all" ? undefined : status;
      return api.skills({ status: apiStatus, limit: 50 });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ skillId, newStatus }: { skillId: string; newStatus: string }) =>
      api.updateSkillStatus(skillId, newStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });

  const handleStatusChange = useCallback((skillId: string, newStatus: string) => {
    statusMutation.mutate({ skillId, newStatus });
  }, [statusMutation]);

  const { filteredItems, query, setQuery } = useTableFilter({
    items: data?.items ?? [],
    searchFields: ["name", "status", "version"],
  });

  const cols = useResizableColumns(COLS);
  const selected = data?.items.find((s) => s.skill_id === selectedId);

  return (
    <div className="flex h-full">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Control bar */}
        <div className="flex shrink-0 items-center gap-3 border-b border-line/30 px-4 py-1.5">
          <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.1em] text-text-0">Skills</span>

          <FilterInput value={query} onChange={setQuery} placeholder="filter skills..." />

          <div className="toggle-group">
            <button className={layout === "compact" ? "active" : ""} onClick={() => setLayout("compact")}>
              <IconList size={11} className="mr-0.5 inline" />list
            </button>
            <button className={layout === "cards" ? "active" : ""} onClick={() => setLayout("cards")}>
              <IconGrid size={11} className="mr-0.5 inline" />grid
            </button>
          </div>

          <div className="ml-auto toggle-group">
            {FILTERS.map((f) => (
              <button key={f} className={status === f ? "active" : ""} onClick={() => setStatus(f)}>{f}</button>
            ))}
          </div>
          <span className="font-mono text-[9px] tabular-nums text-text-3">{filteredItems.length} skills</span>
        </div>

        {/* Column headers (compact only) */}
        {layout === "compact" && (
          <div className="section-rule gap-0">
            {[
              { key: "name", label: "name" },
              { key: "version", label: "ver" },
              { key: "status", label: "status" },
              { key: "success", label: "success", right: true },
              { key: "avg_turns", label: "avg turns", right: true },
              { key: "seen", label: "seen", right: true },
              { key: "triggers", label: "triggers", flex: true },
              { key: "actions", label: "actions", right: true },
              { key: "updated", label: "updated", right: true },
            ].map((col) => (
              <span
                key={col.key}
                className={cn("relative shrink-0", col.flex && "min-w-0 flex-1", col.right && "text-right")}
                style={!col.flex && cols.widths[col.key] ? { width: cols.widths[col.key], flexShrink: 0 } : undefined}
              >
                {col.label}
                {!col.flex && <div {...cols.getResizeHandleProps(col.key)} />}
              </span>
            ))}
          </div>
        )}

        {/* Data rows */}
        <div className="relative min-h-0 flex-1 overflow-y-auto">
          {filteredItems.length > 0 ? (
            layout === "cards" ? (
              <div className="grid grid-cols-2 gap-3 p-4 xl:grid-cols-3">
                {filteredItems.map((skill) => (
                  <SkillCard key={skill.skill_id} skill={skill} onSelect={setSelectedId} onStatusChange={handleStatusChange} />
                ))}
              </div>
            ) : (
              <div>
                {filteredItems.map((skill) => {
                  const m = skill.metrics_json ?? {};
                  const rate = m.success_rate as number | undefined;
                  const turns = m.avg_turns as number | undefined;
                  const count = m.occurrences as number | undefined;
                  const triggers = skill.trigger_json as { keywords?: string[] } | null;
                  const isSelected = selectedId === skill.skill_id;
                  const displayStatus = statusLabel(skill.status);

                  return (
                    <div
                      key={skill.skill_id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedId(isSelected ? null : skill.skill_id)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedId(isSelected ? null : skill.skill_id); } }}
                      className={cn("data-row", isSelected && "selected")}
                    >
                      <span className="shrink-0 truncate font-medium text-text-0"
                        style={cols.widths.name ? { width: cols.widths.name, flexShrink: 0 } : { width: 200, flexShrink: 0 }}>
                        {skill.name}
                      </span>
                      <span className="shrink-0 text-text-3"
                        style={cols.widths.version ? { width: cols.widths.version, flexShrink: 0 } : { width: 60, flexShrink: 0 }}>
                        {skill.version}
                      </span>
                      <span className={cn("shrink-0 text-[10px] font-semibold uppercase", STATUS_COLOR[displayStatus] ?? "text-text-3")}
                        style={cols.widths.status ? { width: cols.widths.status, flexShrink: 0 } : { width: 80, flexShrink: 0 }}>
                        {displayStatus}
                      </span>
                      <span className="shrink-0 text-right tabular-nums text-ok"
                        style={cols.widths.success ? { width: cols.widths.success, flexShrink: 0 } : { width: 70, flexShrink: 0 }}>
                        {rate !== undefined ? `${(rate * 100).toFixed(0)}%` : "--"}
                      </span>
                      <span className="shrink-0 text-right tabular-nums text-text-1"
                        style={cols.widths.avg_turns ? { width: cols.widths.avg_turns, flexShrink: 0 } : { width: 70, flexShrink: 0 }}>
                        {turns !== undefined ? turns.toFixed(1) : "--"}
                      </span>
                      <span className="shrink-0 text-right tabular-nums text-text-2"
                        style={cols.widths.seen ? { width: cols.widths.seen, flexShrink: 0 } : { width: 60, flexShrink: 0 }}>
                        {count ?? "--"}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-text-3">
                        {triggers?.keywords?.join(", ") ?? ""}
                      </span>
                      <span className="shrink-0 flex items-center justify-end gap-1"
                        style={cols.widths.actions ? { width: cols.widths.actions, flexShrink: 0 } : { width: 120, flexShrink: 0 }}>
                        {skill.status === "candidate" && (
                          <>
                            <button onClick={(e) => { e.stopPropagation(); handleStatusChange(skill.skill_id, "validated"); }}
                              className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-accent bg-accent-dim hover:bg-accent hover:text-void-0 transition-colors">
                              <IconZap size={9} /> promote
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); handleStatusChange(skill.skill_id, "rejected"); }}
                              className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-err bg-err-dim hover:bg-err hover:text-void-0 transition-colors">
                              <IconX size={9} /> reject
                            </button>
                          </>
                        )}
                        {skill.status === "validated" && (
                          <>
                            <button onClick={(e) => { e.stopPropagation(); handleStatusChange(skill.skill_id, "promoted"); }}
                              className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-ok bg-ok-dim hover:bg-ok hover:text-void-0 transition-colors">
                              <IconPlay size={9} /> build
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); handleStatusChange(skill.skill_id, "rejected"); }}
                              className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-err bg-err-dim hover:bg-err hover:text-void-0 transition-colors">
                              <IconX size={9} /> reject
                            </button>
                          </>
                        )}
                      </span>
                      <span className="shrink-0 text-right text-[10px] tabular-nums text-text-3"
                        style={cols.widths.updated ? { width: cols.widths.updated, flexShrink: 0 } : { width: 80, flexShrink: 0 }}>
                        {timeAgo(skill.updated_ts)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )
          ) : (
            <EmptyState title="No skills yet" description="Skills are mined from repeated patterns. Keep tracing." />
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selected && (
        <>
          <div className="dither-overlay anim-fade-in fixed inset-0 z-40 cursor-pointer" onClick={() => setSelectedId(null)} />
          <div className="fixed inset-y-0 right-0 z-50">
            <div className="anim-slide-in flex h-full w-[480px] shrink-0 flex-col border-l border-line/50 bg-void-0" style={{ boxShadow: "var(--panel-shadow)" }}>
              <div className="flex shrink-0 items-center justify-between border-b border-line/30 px-4 py-2.5">
                <span className="font-sans text-[9px] font-semibold uppercase tracking-[0.2em] text-text-3">skill detail</span>
                <button onClick={() => setSelectedId(null)} className="rounded px-2 py-0.5 font-sans text-[10px] text-text-3 transition-colors hover:bg-void-2 hover:text-text-0">&times; close</button>
              </div>
              <div className="flex-1 overflow-y-auto">
                <div className="flex flex-wrap items-center gap-4 border-b border-line/30 bg-void-1/50 px-4 py-2.5">
                  <div className="stat-pip"><span className="stat-value">{selected.version}</span><span className="stat-label">version</span></div>
                  <div className="stat-pip"><span className={cn("stat-value", STATUS_COLOR[statusLabel(selected.status)])}>{statusLabel(selected.status)}</span><span className="stat-label">status</span></div>
                  {(selected.metrics_json?.success_rate as number | undefined) !== undefined && (
                    <div className="stat-pip"><span className="stat-value text-ok">{((selected.metrics_json!.success_rate as number) * 100).toFixed(0)}%</span><span className="stat-label">success</span></div>
                  )}
                  {(selected.metrics_json?.avg_turns as number | undefined) !== undefined && (
                    <div className="stat-pip"><span className="stat-value">{(selected.metrics_json!.avg_turns as number).toFixed(1)}</span><span className="stat-label">avg turns</span></div>
                  )}
                  <span className="font-mono text-[10px] tabular-nums text-text-3">{timeAgo(selected.updated_ts)}</span>
                </div>

                {/* Action buttons in panel */}
                {(selected.status === "candidate" || selected.status === "validated") && (
                  <div className="flex items-center gap-2 border-b border-line/20 px-4 py-2.5">
                    {selected.status === "candidate" && (
                      <button onClick={() => handleStatusChange(selected.skill_id, "validated")} className="flex items-center gap-1 rounded px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-accent bg-accent-dim hover:bg-accent hover:text-void-0 transition-colors">
                        <IconZap size={10} /> promote to validated
                      </button>
                    )}
                    {selected.status === "validated" && (
                      <button onClick={() => handleStatusChange(selected.skill_id, "promoted")} className="flex items-center gap-1 rounded px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-ok bg-ok-dim hover:bg-ok hover:text-void-0 transition-colors">
                        <IconPlay size={10} /> build skill
                      </button>
                    )}
                    <button onClick={() => handleStatusChange(selected.skill_id, "rejected")} className="flex items-center gap-1 rounded px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-err bg-err-dim hover:bg-err hover:text-void-0 transition-colors">
                      <IconX size={10} /> reject
                    </button>
                  </div>
                )}

                <div className="border-b border-line/20 px-4 py-3">
                  <div className="mb-1 font-sans text-[9px] font-semibold uppercase tracking-[0.15em] text-text-3">Name</div>
                  <div className="font-mono text-[13px] font-medium text-text-0">{selected.name}</div>
                </div>
                {selected.steps_json && (
                  <div className="border-b border-line/20 px-4 py-3">
                    <div className="mb-1.5 font-sans text-[9px] font-semibold uppercase tracking-[0.15em] text-text-3">Steps</div>
                    <div className="space-y-1">
                      {(selected.steps_json as string[]).map((step, i) => (
                        <div key={i} className="flex gap-2 font-mono text-[11px]">
                          <span className="w-4 shrink-0 text-right tabular-nums text-text-3">{i + 1}</span>
                          <span className="text-text-1">{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {selected.checks_json && (
                  <div className="border-b border-line/20 px-4 py-3">
                    <div className="mb-1.5 font-sans text-[9px] font-semibold uppercase tracking-[0.15em] text-text-3">Checks</div>
                    <div className="flex flex-wrap gap-1.5">
                      {(selected.checks_json as string[]).map((check, i) => (
                        <span key={i} className="rounded bg-void-2 px-2 py-0.5 font-mono text-[10px] text-text-2">{check}</span>
                      ))}
                    </div>
                  </div>
                )}
                {selected.trigger_json && (
                  <div className="px-4 py-3">
                    <div className="mb-1.5 font-sans text-[9px] font-semibold uppercase tracking-[0.15em] text-text-3">Triggers</div>
                    <pre className="overflow-x-auto rounded border border-line/30 bg-void-1 p-3 font-mono text-[9px] leading-relaxed text-text-2">
                      {JSON.stringify(selected.trigger_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
