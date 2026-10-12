import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Menu, Sparkles, ShieldCheck, ExternalLink } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { cn } from "@/lib/utils";

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Accessibility Audit Engine",
    subtitle: "Real-time headless DOM extraction, computed styles & WCAG 2.1 AA/AAA analysis",
  },
  "/screenshot-lab": {
    title: "AI Screenshot Lab",
    subtitle: "Multimodal Gemini vision analysis & autonomous UI code reconstruction",
  },
  "/patch-lab": {
    title: "CSS Remediation Sandbox",
    subtitle: "Inject synthesized CSS patches and verify visual compliance in headless browser",
  },
  "/wcag": {
    title: "WCAG 2.1 Standards Reference",
    subtitle: "Complete mathematical criteria, luminance formulas, and compliance matrix",
  },
};

export function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const page = pageTitles[location.pathname] ?? pageTitles["/"];

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-row font-sans antialiased">
      {/* ── Mobile overlay ── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Desktop sticky sidebar ── */}
      <div className="hidden md:block shrink-0 sticky top-0 h-screen z-30">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      </div>

      {/* ── Mobile drawer sidebar ── */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 md:hidden transition-transform duration-300 ease-out",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
      </div>

      {/* ── Main content area ── */}
      <div className="flex-1 min-w-0 flex flex-col min-h-screen bg-[#f8fafc]">
        {/* Top header bar */}
        <header className="sticky top-0 z-20 h-16 bg-white border-b border-slate-200/80 px-6 flex items-center justify-between gap-4 shrink-0 shadow-[0_1px_3px_0_rgba(0,0,0,0.02)]">
          <div className="flex items-center gap-3 min-w-0">
            <button
              className="md:hidden text-slate-500 hover:text-slate-900 p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={18} />
            </button>

            <div className="min-w-0">
              <h1 className="text-base font-bold text-slate-900 tracking-tight truncate flex items-center gap-2">
                {page.title}
              </h1>
              <p className="text-xs text-slate-500 hidden sm:block truncate">
                {page.subtitle}
              </p>
            </div>
          </div>

          {/* Right badges & controls */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold">
              <Sparkles size={13} className="text-blue-600" />
              <span>Gemini 3.5 Flash</span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold">
              <ShieldCheck size={13} className="text-emerald-600" />
              <span>WCAG 2.1 AA/AAA</span>
            </div>

            <a
              href="https://github.com/Ameythepro/VisionGuard-AI-Autonomous-Agentic-UI-UX-WCAG-Accessibility-Auditor"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors shadow-sm"
              title="View on GitHub"
            >
              <svg className="w-3.5 h-3.5 fill-slate-700" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              <span className="hidden sm:inline">GitHub</span>
              <ExternalLink size={11} className="text-slate-400" />
            </a>
          </div>
        </header>

        {/* Page content view */}
        <div className="flex-1 p-6 lg:p-8 w-full max-w-7xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
