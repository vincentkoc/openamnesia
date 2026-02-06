import { Brain, TrendingUp, Clock } from "lucide-react";
import type { Skill } from "../../lib/api";
import { Badge } from "../common/Badge";
import { timeAgo, truncate } from "../../lib/utils";

interface SkillCardProps {
  skill: Skill;
}

export function SkillCard({ skill }: SkillCardProps) {
  const metrics = skill.metrics_json ?? {};
  const successRate = metrics.success_rate as number | undefined;
  const avgTurns = metrics.avg_turns as number | undefined;

  return (
    <div className="animate-fade-in rounded-xl border border-cream-300 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:border-cream-400 hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-50">
            <Brain className="h-4 w-4 text-accent-600" />
          </div>
          <div>
            <h3 className="text-[14px] font-semibold text-ink-400">
              {truncate(skill.name, 40)}
            </h3>
            <span className="text-[11px] text-ink-50">
              {skill.version} &middot; {timeAgo(skill.updated_ts)}
            </span>
          </div>
        </div>
        <Badge
          variant={
            skill.status === "validated"
              ? "success"
              : skill.status === "candidate"
                ? "accent"
                : "default"
          }
        >
          {skill.status}
        </Badge>
      </div>

      {/* Metrics row */}
      <div className="mt-4 flex items-center gap-4">
        {successRate !== undefined && (
          <div className="flex items-center gap-1.5">
            <TrendingUp className="h-3.5 w-3.5 text-success-500" />
            <span className="text-[12px] font-medium text-ink-200">
              {(successRate * 100).toFixed(0)}% success
            </span>
          </div>
        )}
        {avgTurns !== undefined && (
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-ink-50" />
            <span className="text-[12px] text-ink-50">
              {avgTurns.toFixed(1)} avg turns
            </span>
          </div>
        )}
      </div>

      {/* Triggers preview */}
      {skill.trigger_json && (
        <div className="mt-3 overflow-hidden rounded-lg bg-cream-50 p-2.5">
          <span className="text-[11px] font-medium text-ink-50">Triggers</span>
          <p className="mt-0.5 font-mono text-[11px] text-ink-100">
            {truncate(JSON.stringify(skill.trigger_json), 120)}
          </p>
        </div>
      )}
    </div>
  );
}
