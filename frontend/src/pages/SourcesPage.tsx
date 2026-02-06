import { useQuery } from "@tanstack/react-query";
import { Cpu, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import { SourceCard } from "../components/sources/SourceCard";
import { EmptyState } from "../components/common/EmptyState";
import { numberFormat, formatDateTime } from "../lib/utils";

export function SourcesPage() {
  const { data: sources, refetch, isFetching } = useQuery({
    queryKey: ["sources"],
    queryFn: api.sources,
  });

  const { data: audit } = useQuery({
    queryKey: ["audit"],
    queryFn: () => api.audit({ limit: 10 }),
  });

  return (
    <div className="px-8 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink-500">
            Sources
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-50">
            Connected data sources and ingestion status
          </p>
        </div>
        <button
          onClick={() => void refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-cream-300 bg-white px-3 py-2 text-[12px] font-medium text-ink-200 shadow-sm transition-colors hover:bg-cream-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Source cards */}
      {sources && sources.items.length > 0 ? (
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sources.items.map((src) => (
            <SourceCard key={src.source} source={src} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No sources connected"
          description="Configure sources in config.yaml and run the daemon to start ingesting."
        />
      )}

      {/* Audit log */}
      {audit && audit.items.length > 0 && (
        <div className="rounded-xl border border-cream-300 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <div className="border-b border-cream-200 px-5 py-3 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-ink-50" />
            <h2 className="text-[14px] font-semibold text-ink-400">Recent Ingestion Runs</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="border-b border-cream-200 text-ink-50">
                  <th className="px-5 py-2.5 font-medium">Time</th>
                  <th className="px-5 py-2.5 font-medium">Source</th>
                  <th className="px-5 py-2.5 font-medium text-right">Events</th>
                  <th className="px-5 py-2.5 font-medium text-right">Sessions</th>
                  <th className="px-5 py-2.5 font-medium text-right">Moments</th>
                  <th className="px-5 py-2.5 font-medium text-right">Skills</th>
                </tr>
              </thead>
              <tbody>
                {audit.items.map((row, i) => (
                  <tr key={i} className="border-b border-cream-100 last:border-b-0 hover:bg-cream-50 transition-colors">
                    <td className="px-5 py-2.5 text-ink-100">
                      {formatDateTime(row.ts as string)}
                    </td>
                    <td className="px-5 py-2.5 font-medium capitalize text-ink-200">
                      {row.source as string}
                    </td>
                    <td className="px-5 py-2.5 text-right tabular-nums text-ink-100">
                      {numberFormat(row.event_count as number)}
                    </td>
                    <td className="px-5 py-2.5 text-right tabular-nums text-ink-100">
                      {numberFormat(row.session_count as number)}
                    </td>
                    <td className="px-5 py-2.5 text-right tabular-nums text-ink-100">
                      {numberFormat(row.moment_count as number)}
                    </td>
                    <td className="px-5 py-2.5 text-right tabular-nums text-ink-100">
                      {numberFormat(row.skill_count as number)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
