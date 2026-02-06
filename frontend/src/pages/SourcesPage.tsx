import { useQuery } from "@tanstack/react-query";
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
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-[1100px]">
        {/* Header */}
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-[24px] font-bold tracking-tight text-text-0">
              sources
            </h1>
            <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-text-3">
              connected data sources &amp; ingestion
            </p>
          </div>
          <button
            onClick={() => void refetch()}
            disabled={isFetching}
            className="rounded border border-line/50 px-3 py-1.5 text-[9px] font-medium uppercase tracking-[0.15em] text-text-2 transition-colors hover:border-accent hover:text-accent disabled:opacity-50"
          >
            {isFetching ? "syncing..." : "refresh"}
          </button>
        </div>

        {sources && sources.items.length > 0 ? (
          <div className="stagger mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {sources.items.map((src) => (
              <SourceCard key={src.source} source={src} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No sources"
            description="Configure sources in config.yaml and run the daemon."
          />
        )}

        {/* Audit */}
        {audit && audit.items.length > 0 && (
          <div>
            <div className="mb-3 flex items-center gap-3">
              <div className="h-px flex-1 bg-line/30" />
              <span className="text-[9px] uppercase tracking-[0.2em] text-text-3">
                recent runs
              </span>
              <div className="h-px flex-1 bg-line/30" />
            </div>
            <div className="overflow-hidden rounded border border-line/40">
              <table className="w-full text-left text-[10px]">
                <thead>
                  <tr className="border-b border-line/50 text-text-3">
                    <th className="px-4 py-2 font-medium uppercase tracking-[0.15em]">
                      time
                    </th>
                    <th className="px-4 py-2 font-medium uppercase tracking-[0.15em]">
                      source
                    </th>
                    <th className="px-4 py-2 text-right font-medium uppercase tracking-[0.15em]">
                      events
                    </th>
                    <th className="px-4 py-2 text-right font-medium uppercase tracking-[0.15em]">
                      sessions
                    </th>
                    <th className="px-4 py-2 text-right font-medium uppercase tracking-[0.15em]">
                      moments
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {audit.items.map((row, i) => (
                    <tr
                      key={i}
                      className="border-b border-line/20 transition-colors last:border-b-0 hover:bg-void-1/30"
                    >
                      <td className="px-4 py-2 tabular-nums text-text-2">
                        {formatDateTime(row.ts as string)}
                      </td>
                      <td className="px-4 py-2 font-semibold text-text-1">
                        {row.source as string}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-text-1">
                        {numberFormat(row.event_count as number)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-text-2">
                        {numberFormat(row.session_count as number)}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-text-2">
                        {numberFormat(row.moment_count as number)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
