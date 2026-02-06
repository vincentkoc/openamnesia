import { cn } from "../../lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "ok" | "warn" | "err" | "accent";
  className?: string;
}

const variants: Record<string, string> = {
  default: "bg-void-3 text-text-2",
  ok: "bg-ok-dim text-ok",
  warn: "bg-warn-dim text-warn",
  err: "bg-err-dim text-err",
  accent: "bg-accent-dim text-accent",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span className={cn("inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-medium tracking-wide", variants[variant], className)}>
      {children}
    </span>
  );
}
