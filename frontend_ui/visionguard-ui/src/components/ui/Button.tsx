import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg" | "icon";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary: [
    "bg-accent text-text-inverse border border-accent",
    "hover:bg-accent-hover hover:border-accent-hover",
    "active:scale-[0.98] active:brightness-95",
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
    "focus-visible:ring-2 focus-visible:ring-accent/40",
  ].join(" "),

  secondary: [
    "bg-bg-surface text-text-primary border border-border",
    "hover:bg-bg-subtle hover:border-border-strong",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
  ].join(" "),

  outline: [
    "bg-transparent text-accent border border-accent",
    "hover:bg-accent-subtle",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
  ].join(" "),

  ghost: [
    "bg-transparent text-text-secondary border border-transparent",
    "hover:bg-bg-subtle hover:text-text-primary",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
  ].join(" "),

  danger: [
    "bg-danger text-text-inverse border border-danger",
    "hover:brightness-90",
    "active:scale-[0.98]",
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
  ].join(" "),
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5 rounded",
  md: "h-9 px-4 text-sm gap-2 rounded",
  lg: "h-10 px-5 text-sm gap-2 rounded-md",
  icon: "h-9 w-9 rounded flex-shrink-0",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = "primary", size = "md", loading = false, className, children, disabled, ...props },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center font-medium",
          "transition-all duration-150 ease-out",
          "select-none whitespace-nowrap",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading ? (
          <>
            <svg
              className="animate-spin h-4 w-4 shrink-0"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            <span>{children}</span>
          </>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
