import { cn, sourceColor } from "../../lib/utils";

interface SourceBadgeProps {
  source: string;
  className?: string;
}

export function SourceBadge({ source, className }: SourceBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md bg-cream-200 px-2 py-0.5 text-[11px] font-medium text-ink-100",
        className,
      )}
    >
      <span className={cn("h-2 w-2 rounded-full", sourceColor(source))} />
      {source}
    </span>
  );
}
