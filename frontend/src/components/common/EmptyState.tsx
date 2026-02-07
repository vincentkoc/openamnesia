import { IconBrain, IconActivity, IconDatabase } from "./Icons";

const ICONS = {
  moments: IconBrain,
  events: IconActivity,
  default: IconDatabase,
} as const;

export function EmptyState({
  title = "No data yet",
  description = "Data will appear here once the daemon starts ingesting.",
  icon = "default",
}: {
  title?: string;
  description?: string;
  icon?: keyof typeof ICONS;
}) {
  const IconComp = ICONS[icon];

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="anim-float mb-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-line/40 bg-void-1">
          <IconComp size={24} className="text-text-3" />
        </div>
      </div>
      <h3 className="font-mono text-[13px] font-medium text-text-1">{title}</h3>
      <p className="mt-1.5 max-w-[280px] font-sans text-[11px] leading-relaxed text-text-3">
        {description}
      </p>
      <div className="mt-4 flex items-center gap-1.5">
        <span className="h-1 w-1 rounded-full bg-text-3/40 anim-pulse" style={{ animationDelay: "0s" }} />
        <span className="h-1 w-1 rounded-full bg-text-3/40 anim-pulse" style={{ animationDelay: "0.5s" }} />
        <span className="h-1 w-1 rounded-full bg-text-3/40 anim-pulse" style={{ animationDelay: "1s" }} />
      </div>
    </div>
  );
}
