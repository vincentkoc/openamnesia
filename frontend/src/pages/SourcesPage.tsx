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
    <div>
      {/* Header */}
      <div className="mb-12 flex items-end justify-between">
        <div>
          <h1 className="font-serif text-[48px] font-normal italic leading-none tracking-tight text-text-0">
            Sources
          </h1>
          <p className="mt-3 text-[10px] uppercase tracking-[0.3em] text-text-3">
            Connected data sources &amp; ingestion
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
        <div className="stagger mb-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
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
          <div className="mb-4 flex items-center gap-4">
            <div className="h-px flex-1 bg-line/30" />
            <span className="text-[9px] uppercase tracking-[0.2em] text-text-3">
              Recent Runs
            </span>
            <div className="h-px flex-1 bg-line/30" />
          </div>
          <div className="overflow-hidden rounded-lg border border-line/40 bg-void-1/50">
            <table className="w-full text-left text-[10px]">
              <thead>
                <tr className="border-b border-line/50 text-text-3">
                  <th className="px-4 py-2.5 font-medium uppercase tracking-[0.15em]">time</th>
                  <th className="px-4 py-2.5 font-medium uppercase tracking-[0.15em]">source</th>
                  <th className="px-4 py-2.5 font-medium uppercase tracking-[0.15em] text-right">events</th>
                  <th className="px-4 py-2.5 font-medium uppercase tracking-[0.15em] text-right">sessions</th>
                  <th className="px-4 py-2.5 font-medium uppercase tracking-[0.15em] text-right">moments</th>
                </tr>
              </thead>
              <tbody>
                {audit.items.map((row, i) => (
                  <tr key={i} className="border-b border-line/20 last:border-b-0 transition-colors hover:bg-void-2/30">
                    <td className="px-4 py-2 tabular-nums text-text-2">
                      {formatDateTime(row.ts as string)}
                    </td>
                    <td className="px-4 py-2 font-semibold capitalize text-text-1">
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
  );
}
