import { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { ScanSearch, FlaskConical, BookOpen, Shield, ChevronLeft, ChevronRight, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { api, type HealthResponse } from "@/lib/api";

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
  description: string;
}

const navItems: NavItem[] = [
  {
    to: "/",
    icon: <ScanSearch size={18} />,
    label: "Audit",
    description: "Run accessibility audits",
  },
  {
    to: "/patch-lab",
    icon: <FlaskConical size={18} />,
    label: "Patch Lab",
    description: "CSS patch sandbox",
  },
  {
    to: "/wcag",
    icon: <BookOpen size={18} />,
    label: "WCAG Guide",
    description: "Accessibility reference",
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const isOnline = health?.status === "healthy";

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-30 flex flex-col",
        "bg-bg-surface border-r border-border",
        "transition-[width] duration-200 ease-out",
        collapsed ? "w-[56px]" : "w-[220px]"
      )}
      aria-label="Main navigation"
    >
      {/* ── Brand ── */}
      <div
        className={cn(
          "flex items-center gap-2.5 h-14 px-3 border-b border-border shrink-0",
          collapsed && "justify-center px-0"
        )}
      >
        <div className="w-7 h-7 bg-accent rounded flex items-center justify-center shrink-0">
          <Shield size={15} className="text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <p className="text-sm font-semibold text-text-primary leading-tight truncate">
              VisionGuard
            </p>
            <p className="text-2xs text-text-tertiary leading-tight">AI Auditor</p>
          </div>
        )}
      </div>

      {/* ── Nav items ── */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const active =
            item.to === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.to);

          return (
            <NavLink
              key={item.to}
              to={item.to}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-2.5 h-9 px-2.5 rounded",
                "text-sm font-medium transition-colors duration-150",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
                active
                  ? "bg-accent-subtle text-accent"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-subtle",
                collapsed && "justify-center px-0"
              )}
            >
              <span className="shrink-0">{item.icon}</span>
              {!collapsed && (
                <span className="truncate">{item.label}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* ── API status ── */}
      {!collapsed && (
        <div className="mx-2 mb-3 px-3 py-2.5 rounded bg-bg-subtle border border-border">
          <div className="flex items-center gap-2 mb-0.5">
            <Activity size={12} className={isOnline ? "text-success" : "text-danger"} />
            <span className="text-xs font-medium text-text-primary">
              {isOnline ? "API Online" : "API Offline"}
            </span>
          </div>
          {health && (
            <p className="text-2xs text-text-tertiary leading-relaxed">
              v{health.version} · Redis{" "}
              {health.redis_connected ? "connected" : "offline"}
            </p>
          )}
          {!health && (
            <p className="text-2xs text-danger">
              Cannot reach localhost:8000
            </p>
          )}
        </div>
      )}

      {/* ── Collapse toggle ── */}
      <button
        onClick={onToggle}
        className={cn(
          "flex items-center justify-center h-9 border-t border-border",
          "text-text-tertiary hover:text-text-primary hover:bg-bg-subtle",
          "transition-colors duration-150 shrink-0",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        )}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  );
}
