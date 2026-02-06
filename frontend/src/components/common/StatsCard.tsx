import { cn } from "../../lib/utils";

interface StatsCardProps {
  label: string;
  value: string | number;
  sub?: string;
  className?: string;
}

export function StatsCard({ label, value, sub, className }: StatsCardProps) {
  return (
    <div className={cn("group text-center", className)}>
      <div className="text-[28px] font-bold tabular-nums leading-none tracking-tight text-text-0 transition-colors group-hover:text-accent">
        {value}
      </div>
      <div className="mt-1.5 text-[8px] font-medium uppercase tracking-[0.2em] text-text-3">
        {label}
      </div>
      {sub && <div className="text-[8px] text-text-3">{sub}</div>}
    </div>
  );
}
