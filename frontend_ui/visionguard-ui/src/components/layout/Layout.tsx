import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { cn } from "@/lib/utils";

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Accessibility Audit",
    subtitle: "Analyse any URL for WCAG 2.1 violations",
  },
  "/patch-lab": {
    title: "CSS Patch Lab",
    subtitle: "Inject CSS patches and compare before/after screenshots",
  },
  "/wcag": {
    title: "WCAG Guide",
    subtitle: "Web Content Accessibility Guidelines 2.1 reference",
  },
};

export function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const page = pageTitles[location.pathname] ?? pageTitles["/"];

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Collapse sidebar on small screens automatically
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    if (mq.matches) setCollapsed(true);
    const handler = (e: MediaQueryListEvent) => setCollapsed(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const sidebarWidth = collapsed ? 56 : 220;

  return (
    <div className="min-h-screen bg-bg-base">
      {/* ── Mobile overlay ── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/30 backdrop-blur-[1px] md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Desktop sidebar ── */}
      <div className="hidden md:block">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      </div>

      {/* ── Mobile sidebar drawer ── */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-40 md:hidden",
          "transition-transform duration-250 ease-out",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
      </div>

      {/* ── Main content ── */}
      <main
        className="flex flex-col min-h-screen transition-[margin-left] duration-200 ease-out"
        style={{ marginLeft: typeof window !== "undefined" && window.innerWidth >= 768 ? sidebarWidth : 0 }}
      >
        {/* Top header bar */}
        <header className="sticky top-0 z-10 h-14 bg-bg-surface border-b border-border flex items-center px-5 gap-4 shrink-0">
          {/* Mobile menu toggle */}
          <button
            className="md:hidden text-text-secondary hover:text-text-primary transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent rounded"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>

          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-text-primary truncate">
              {page.title}
            </h1>
            <p className="text-xs text-text-tertiary hidden sm:block truncate">
              {page.subtitle}
            </p>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 p-5 lg:p-7 animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
