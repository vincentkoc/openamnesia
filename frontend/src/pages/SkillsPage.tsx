import { useQuery } from "@tanstack/react-query";
import { Brain } from "lucide-react";
import { api } from "../lib/api";
import { SkillCard } from "../components/skills/SkillCard";
import { EmptyState } from "../components/common/EmptyState";
import { useState } from "react";

const STATUS_FILTERS = ["all", "candidate", "validated", "promoted"] as const;

export function SkillsPage() {
  const [status, setStatus] = useState<string>("all");

  const { data } = useQuery({
    queryKey: ["skills", status],
    queryFn: () =>
      api.skills({
        status: status === "all" ? undefined : status,
        limit: 50,
      }),
  });

  return (
    <div className="px-8 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink-500">
            Skills
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-50">
            Reusable workflow patterns mined from your sessions
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-cream-200 p-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatus(f)}
              className={`rounded-md px-3 py-1.5 text-[12px] font-medium capitalize transition-colors ${
                status === f
                  ? "bg-white text-ink-400 shadow-sm"
                  : "text-ink-50 hover:text-ink-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Count */}
      {data && data.total > 0 && (
        <div className="mb-4 flex items-center gap-2 text-[12px] text-ink-50">
          <Brain className="h-3.5 w-3.5" />
          {data.total} skill{data.total !== 1 ? "s" : ""}
        </div>
      )}

      {/* Grid */}
      {data && data.items.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((skill) => (
            <SkillCard key={skill.skill_id} skill={skill} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No skills extracted yet"
          description="Skills are mined from repeated patterns in your sessions. Keep using your tools and Amnesia will detect them."
        />
      )}
    </div>
  );
}
