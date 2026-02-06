import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
}

export function EmptyState({
  title = "No data yet",
  description = "Data will appear here once the daemon starts ingesting sources.",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 rounded-2xl bg-cream-200 p-4">
        <Inbox className="h-8 w-8 text-cream-500" />
      </div>
      <h3 className="text-[15px] font-medium text-ink-300">{title}</h3>
      <p className="mt-1 max-w-xs text-[13px] text-ink-50">{description}</p>
    </div>
  );
}
