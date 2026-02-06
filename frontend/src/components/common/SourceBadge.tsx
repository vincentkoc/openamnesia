import { cn, sourceColor } from "../../lib/utils";

export function SourceBadge({ source, className }: { source: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 text-[10px] font-medium bg-void-3 text-text-1", className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", sourceColor(source))} />
      {source}
    </span>
  );
}
