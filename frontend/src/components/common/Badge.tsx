import { cn } from "../../lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "accent";
  className?: string;
}

const variants: Record<string, string> = {
  default: "bg-cream-200 text-ink-100",
  success: "bg-success-100 text-success-500",
  warning: "bg-warning-100 text-warning-500",
  error: "bg-error-100 text-error-500",
  accent: "bg-accent-50 text-accent-600",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium",
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
