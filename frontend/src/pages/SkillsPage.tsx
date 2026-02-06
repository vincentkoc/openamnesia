import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { SkillCard } from "../components/skills/SkillCard";
import { EmptyState } from "../components/common/EmptyState";
import { useState } from "react";

const FILTERS = ["all", "candidate", "validated", "promoted"] as const;

export function SkillsPage() {
  const [status, setStatus] = useState("all");

  const { data } = useQuery({
    queryKey: ["skills", status],
    queryFn: () => api.skills({ status: status === "all" ? undefined : status, limit: 50 }),
  });

  return (
    <div>
      {/* Header */}
      <div className="mb-12 flex items-end justify-between">
        <div>
          <h1 className="font-serif text-[48px] font-normal italic leading-none tracking-tight text-text-0">
            Skills
          </h1>
          <p className="mt-3 text-[10px] uppercase tracking-[0.3em] text-text-3">
            Reusable workflow patterns mined from traces
          </p>
        </div>
        <div className="flex items-center gap-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatus(f)}
              className={`rounded px-3 py-1.5 text-[9px] font-medium uppercase tracking-[0.15em] transition-colors ${
                status === f
                  ? "bg-accent text-void-0"
                  : "text-text-3 hover:text-text-1"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {data && data.total > 0 && (
        <div className="mb-6 text-[9px] tabular-nums uppercase tracking-[0.2em] text-text-3">
          {data.total} skill{data.total !== 1 ? "s" : ""}
        </div>
      )}

      {data && data.items.length > 0 ? (
        <div className="stagger grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((skill) => (
            <SkillCard key={skill.skill_id} skill={skill} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No skills yet"
          description="Skills are mined from repeated patterns. Keep tracing."
        />
      )}
    </div>
  );
}
