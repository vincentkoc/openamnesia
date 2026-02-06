import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

interface StatsCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: ReactNode;
  className?: string;
}

export function StatsCard({ label, value, sub, icon, className }: StatsCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-cream-300 bg-white px-5 py-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-medium uppercase tracking-wider text-ink-50">
          {label}
        </span>
        {icon && <span className="text-cream-400">{icon}</span>}
      </div>
      <div className="mt-1.5 text-2xl font-semibold tracking-tight text-ink-500">
        {value}
      </div>
      {sub && <div className="mt-0.5 text-[12px] text-ink-50">{sub}</div>}
    </div>
  );
}
