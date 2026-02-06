import type { Skill } from "../../lib/api";
import { Badge } from "../common/Badge";
import { timeAgo, truncate } from "../../lib/utils";

interface Props {
  skill: Skill;
}

export function SkillCard({ skill }: Props) {
  const m = skill.metrics_json ?? {};
  const rate = m.success_rate as number | undefined;
  const turns = m.avg_turns as number | undefined;
  const count = m.occurrences as number | undefined;

  return (
    <div className="glow-border group rounded-lg border border-line bg-void-1 p-4 transition-colors hover:border-line-bright hover:bg-void-2">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-[13px] font-semibold text-text-0 group-hover:text-accent-bright transition-colors">
            {truncate(skill.name, 35)}
          </h3>
          <div className="mt-0.5 text-[10px] text-text-3">
            {skill.version} &middot; {timeAgo(skill.updated_ts)}
          </div>
        </div>
        <Badge variant={skill.status === "promoted" ? "ok" : skill.status === "validated" ? "accent" : "default"}>
          {skill.status}
        </Badge>
      </div>

      {/* Metrics — big numbers */}
      <div className="mt-3 grid grid-cols-3 gap-2">
        {rate !== undefined && (
          <div className="rounded-md bg-void-2 px-2 py-1.5 text-center">
            <div className="text-[14px] font-bold tabular-nums text-ok">
              {(rate * 100).toFixed(0)}%
            </div>
            <div className="text-[9px] uppercase tracking-wider text-text-3">success</div>
          </div>
        )}
        {turns !== undefined && (
          <div className="rounded-md bg-void-2 px-2 py-1.5 text-center">
            <div className="text-[14px] font-bold tabular-nums text-text-0">
              {turns.toFixed(1)}
            </div>
            <div className="text-[9px] uppercase tracking-wider text-text-3">avg turns</div>
          </div>
        )}
        {count !== undefined && (
          <div className="rounded-md bg-void-2 px-2 py-1.5 text-center">
            <div className="text-[14px] font-bold tabular-nums text-text-0">
              {count}
            </div>
            <div className="text-[9px] uppercase tracking-wider text-text-3">seen</div>
          </div>
        )}
      </div>

      {/* Triggers */}
      {skill.trigger_json && (
        <div className="mt-3 overflow-hidden rounded-md bg-void-0 px-2.5 py-2">
          <pre className="text-[10px] text-text-2 leading-relaxed">
            {truncate(JSON.stringify(skill.trigger_json, null, 1), 140)}
          </pre>
        </div>
      )}
    </div>
  );
}
