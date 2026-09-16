import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  variant?: "default" | "success" | "danger" | "warning" | "accent";
  className?: string;
}

const variantValueClass: Record<NonNullable<StatCardProps["variant"]>, string> = {
  default: "text-text-primary",
  accent:  "text-accent",
  success: "text-success",
  danger:  "text-danger",
  warning: "text-warning",
};

export function StatCard({ label, value, icon, variant = "default", className }: StatCardProps) {
  return (
    <div
      className={cn(
        "bg-bg-surface border border-border rounded-lg p-4",
        "flex flex-col gap-1",
        className
      )}
    >
      <div className="flex items-center gap-1.5 text-text-tertiary">
        {icon && <span className="[&>svg]:w-3.5 [&>svg]:h-3.5">{icon}</span>}
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p
        className={cn(
          "text-2xl font-semibold tabular-nums leading-none mt-0.5",
          variantValueClass[variant]
        )}
      >
        {value}
      </p>
    </div>
  );
}
