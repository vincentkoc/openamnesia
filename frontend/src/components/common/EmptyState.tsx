export function EmptyState({
  title = "No data yet",
  description = "Data will appear here once the daemon starts ingesting.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-3 h-px w-16 bg-line" />
      <h3 className="text-[13px] font-medium text-text-1">{title}</h3>
      <p className="mt-1 max-w-xs text-[11px] text-text-3">{description}</p>
      <div className="mt-3 h-px w-16 bg-line" />
    </div>
  );
}
