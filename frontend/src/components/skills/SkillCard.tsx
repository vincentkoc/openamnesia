import type { Skill } from "../../lib/api";
import { cn, timeAgo, truncate } from "../../lib/utils";
import { IconZap, IconPlay, IconX } from "../common/Icons";

interface Props {
  skill: Skill;
  onSelect?: (id: string) => void;
  onStatusChange?: (skillId: string, status: string) => void;
}

const STATUS_COLOR: Record<string, string> = {
  built: "text-ok",
  validated: "text-accent",
  candidate: "text-text-2",
};

function statusLabel(status: string): string {
  if (status === "promoted") return "built";
  return status;
}

export function SkillCard({ skill, onSelect, onStatusChange }: Props) {
  const m = skill.metrics_json ?? {};
  const rate = m.success_rate as number | undefined;
  const turns = m.avg_turns as number | undefined;
  const count = m.occurrences as number | undefined;
  const triggers = skill.trigger_json as { keywords?: string[] } | null;
  const displayStatus = statusLabel(skill.status);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(skill.skill_id)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect?.(skill.skill_id); } }}
      className="card cursor-pointer rounded-lg border border-line/40 bg-void-1/60 p-3"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[12px] font-medium text-text-0">{truncate(skill.name, 30)}</span>
        <span className={cn("text-[9px] font-semibold uppercase", STATUS_COLOR[displayStatus] ?? "text-text-3")}>
          {displayStatus}
        </span>
      </div>

      <div className="flex items-center gap-3 text-[10px]">
        <span className="font-mono text-text-3">{skill.version}</span>
        {rate !== undefined && <span className="font-mono tabular-nums text-ok">{(rate * 100).toFixed(0)}%</span>}
        {turns !== undefined && <span className="font-mono tabular-nums text-text-1">{turns.toFixed(1)} turns</span>}
        {count !== undefined && <span className="font-mono tabular-nums text-text-2">{count}x</span>}
      </div>

      {triggers?.keywords && (
        <div className="mt-2 flex flex-wrap gap-1">
          {triggers.keywords.slice(0, 4).map((kw, i) => (
            <span key={i} className="rounded bg-void-2 px-1.5 py-0.5 font-mono text-[9px] text-text-3">{kw}</span>
          ))}
        </div>
      )}

      <div className="mt-2 flex items-center justify-between border-t border-line/20 pt-2">
        <span className="font-mono text-[9px] tabular-nums text-text-3">{timeAgo(skill.updated_ts)}</span>
        <div className="flex gap-1">
          {skill.status === "candidate" && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); onStatusChange?.(skill.skill_id, "validated"); }}
                className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-accent bg-accent-dim hover:bg-accent hover:text-void-0 transition-colors"
              >
                <IconZap size={10} /> promote
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onStatusChange?.(skill.skill_id, "rejected"); }}
                className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-err bg-err-dim hover:bg-err hover:text-void-0 transition-colors"
              >
                <IconX size={10} /> reject
              </button>
            </>
          )}
          {skill.status === "validated" && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); onStatusChange?.(skill.skill_id, "promoted"); }}
                className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-ok bg-ok-dim hover:bg-ok hover:text-void-0 transition-colors"
              >
                <IconPlay size={10} /> build
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onStatusChange?.(skill.skill_id, "rejected"); }}
                className="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-err bg-err-dim hover:bg-err hover:text-void-0 transition-colors"
              >
                <IconX size={10} /> reject
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
