import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "accent" | "muted";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default:  "bg-bg-subtle text-text-secondary border border-border",
  accent:   "bg-accent-subtle text-accent border border-accent-muted",
  success:  "bg-success-subtle text-success border border-success-muted",
  warning:  "bg-warning-subtle text-warning border border-warning-muted",
  danger:   "bg-danger-subtle text-danger border border-danger-muted",
  muted:    "bg-bg-subtle text-text-tertiary border border-border",
};

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5",
        "text-xs font-medium rounded",
        "leading-none whitespace-nowrap",
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
