import { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { ScanSearch, FlaskConical, BookOpen, Shield, ChevronLeft, ChevronRight, Activity, Image, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { api, type HealthResponse } from "@/lib/api";

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const navItems: NavItem[] = [
  {
    to: "/",
    icon: <ScanSearch size={18} />,
    label: "Audit Engine",
  },
  {
    to: "/screenshot-lab",
    icon: <Image size={18} />,
    label: "Screenshot Lab",
  },
  {
    to: "/patch-lab",
    icon: <FlaskConical size={18} />,
    label: "Patch Sandbox",
  },
  {
    to: "/wcag",
    icon: <BookOpen size={18} />,
    label: "WCAG 2.1 Guide",
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
        "h-full flex flex-col bg-white border-r border-slate-200 select-none shadow-[1px_0_4px_0_rgba(0,0,0,0.02)] transition-[width] duration-200 ease-in-out",
        collapsed ? "w-[68px]" : "w-[240px]"
      )}
      aria-label="Main navigation"
    >
      {/* ── Brand ── */}
      <div
        className={cn(
          "flex items-center gap-3 h-16 px-4 border-b border-slate-200/80 shrink-0",
          collapsed && "justify-center px-0"
        )}
      >
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-md shadow-blue-500/20 text-white shrink-0">
          <Shield size={19} />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <div className="flex items-center gap-1.5">
              <span className="text-base font-extrabold tracking-tight text-slate-900 truncate">
                VisionGuard
              </span>
              <span className="px-1.5 py-0.2 text-[10px] font-bold bg-blue-100 text-blue-700 rounded-full">
                AI
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium">Autonomous Auditor</p>
          </div>
        )}
      </div>

      {/* ── Nav items ── */}
      <nav className="flex-1 py-4 px-2.5 space-y-1 overflow-y-auto">
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
                "group flex items-center gap-3 h-10 px-3 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-blue-50 text-blue-700 font-semibold shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100",
                collapsed && "justify-center px-0"
              )}
            >
              <span className={cn("shrink-0", active ? "text-blue-600" : "text-slate-500 group-hover:text-slate-800")}>
                {item.icon}
              </span>
              {!collapsed && (
                <span className="truncate">{item.label}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* ── Status Card ── */}
      {!collapsed && (
        <div className="mx-3 mb-3 p-3 rounded-xl bg-slate-50 border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", isOnline ? "bg-emerald-400" : "bg-rose-400")} />
                <span className={cn("relative inline-flex rounded-full h-2 w-2", isOnline ? "bg-emerald-500" : "bg-rose-500")} />
              </span>
              <span className="text-[11px] font-bold text-slate-800 tracking-tight">
                {isOnline ? "AI Engine Online" : "Connecting..."}
              </span>
            </div>
            <Sparkles size={13} className="text-blue-600" />
          </div>

          <div className="space-y-1 text-[11px] text-slate-600">
            <div className="flex items-center justify-between">
              <span>Model</span>
              <span className="font-mono text-slate-800 font-semibold text-[10px] px-1.5 py-0.5 bg-white rounded border border-slate-200">
                Gemini 3.5 Flash
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Latency</span>
              <span className="text-emerald-700 font-mono text-[10px] font-semibold">
                ~320ms
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Collapse toggle button ── */}
      <button
        onClick={onToggle}
        className={cn(
          "flex items-center justify-center h-10 border-t border-slate-200",
          "text-slate-400 hover:text-slate-700 hover:bg-slate-50",
          "transition-colors duration-150 shrink-0",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
        )}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}
      </button>
    </aside>
  );
}
