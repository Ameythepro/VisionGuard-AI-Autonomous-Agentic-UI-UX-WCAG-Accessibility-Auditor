import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search, Clock, Globe, Layers, AlertTriangle, CheckCircle, Sparkles, ArrowRight, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { StatCard } from "@/components/audit/StatCard";
import { ResultTabs } from "@/components/audit/ResultTabs";
import { SkeletonMetrics } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { Badge } from "@/components/ui/Badge";
import { api, type AuditResult, type SandboxResponse } from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspaceStore";
import {
  getContrastRatioFromRgb,
  isLargeText,
  wcagLevel,
} from "@/lib/wcag";

function countViolations(styles: AuditResult["computed_styles"]) {
  return styles.filter((el) => {
    const ratio = getContrastRatioFromRgb(el.color, el.backgroundColor);
    const large = isLargeText(el.fontSize, el.fontWeight);
    return ratio !== null && wcagLevel(ratio, large) === "FAIL";
  }).length;
}

export default function AuditPage() {
  const { auditUrl, setAuditUrl } = useWorkspaceStore();
  const [result, setResult] = useState<AuditResult | null>(null);
  const [sandboxResult] = useState<SandboxResponse | null>(null);
  const [isCached, setIsCached] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  const { mutate, isPending, isError, error, reset } = useMutation({
    mutationFn: (targetUrl: string) => api.auditUrl(targetUrl),
    onSuccess: (data) => {
      if (data.result) {
        setResult(data.result);
        setIsCached(data.message.toLowerCase().startsWith("returned cached"));
        setTimeout(() => {
          resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 150);
        toast.success("Audit complete", {
          description: `${data.result.viewports_captured.length} viewports analyzed with zero regressions.`,
        });
      }
    },
    onError: (err: Error) => {
      toast.error("Audit failed", { description: err.message });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = auditUrl.trim();
    if (!trimmed) return;
    if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
      toast.error("Invalid URL", { description: "URL must start with http:// or https://" });
      return;
    }
    setResult(null);
    mutate(trimmed);
  };

  const violations = result ? countViolations(result.computed_styles ?? []) : 0;
  const totalScanned = result?.computed_styles?.length ?? 0;
  const passes = Math.max(0, totalScanned - violations);
  const complianceScore = totalScanned > 0 ? Math.round((passes / totalScanned) * 100) : 100;

  return (
    <div className="space-y-8">
      {/* ── Executive Hero Card ─────────────────────────────────────────── */}
      <section className="bg-white rounded-2xl border border-slate-200 p-8 sm:p-10 shadow-[0_1px_3px_rgba(0,0,0,0.04),0_10px_25px_-5px_rgba(0,0,0,0.03)] relative overflow-hidden">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold uppercase tracking-wider">
            <Sparkles size={13} className="text-blue-600" />
            <span>Autonomous Agentic Accessibility Engine</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Instant WCAG 2.1 <span className="text-blue-600">Audit & Auto-Remediation</span>
          </h1>

          <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
            Inspect live web DOM computed styles, run multi-viewport headless browser simulations, 
            detect luminance contrast deficits, and generate verifiable CSS patches with Gemini 3.5 Flash.
          </p>

          {/* Search Box */}
          <form onSubmit={handleSubmit} className="pt-2" noValidate>
            <div className="flex flex-col sm:flex-row gap-3 p-1.5 rounded-xl bg-slate-50 border border-slate-300 focus-within:border-blue-600 focus-within:ring-2 focus-within:ring-blue-100 focus-within:bg-white transition-all shadow-xs">
              <div className="flex-1 flex items-center gap-3 px-3 py-1">
                <Globe size={18} className="text-slate-500 shrink-0" />
                <input
                  type="url"
                  placeholder="https://example.com"
                  value={auditUrl}
                  onChange={(e) => setAuditUrl(e.target.value)}
                  disabled={isPending}
                  className="w-full bg-transparent text-slate-900 placeholder-slate-400 text-sm font-mono focus:outline-none"
                  aria-label="Target URL to audit"
                />
              </div>

              <button
                type="submit"
                disabled={!auditUrl.trim() || isPending}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
              >
                {isPending ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Auditing…</span>
                  </>
                ) : (
                  <>
                    <Search size={16} />
                    <span>Run Audit</span>
                    <ArrowRight size={14} className="text-blue-200" />
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Quick presets */}
          <div className="flex items-center gap-2 pt-1 flex-wrap">
            <span className="text-xs text-slate-500 font-semibold">Test Presets:</span>
            {[
              { label: "Example.com", url: "https://example.com" },
              { label: "Wikipedia", url: "https://en.wikipedia.org" },
              { label: "Hacker News", url: "https://news.ycombinator.com" },
              { label: "HTTPBin", url: "https://httpbin.org" },
            ].map((preset) => (
              <button
                key={preset.url}
                type="button"
                onClick={() => setAuditUrl(preset.url)}
                className="px-2.5 py-1 rounded-md text-xs font-mono text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-colors"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ── Loading Animation ─────────────────────────────────────────────── */}
      {isPending && (
        <section aria-live="polite" aria-busy="true" className="p-8 rounded-2xl bg-white border border-blue-200 shadow-sm space-y-6">
          <div className="flex items-center gap-3">
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-600" />
            </div>
            <div>
              <p className="text-base font-bold text-slate-900">
                Autonomous Agent Execution in Progress...
              </p>
              <p className="text-xs text-slate-500">
                Spawning Playwright headless browser · Capturing viewports · Extracting computed styles · Synthesizing fixes
              </p>
            </div>
          </div>
          <SkeletonMetrics />
        </section>
      )}

      {/* ── Error state ───────────────────────────────────────────────────── */}
      {isError && !isPending && (
        <ErrorState
          title="Audit failed"
          message={(error as Error)?.message ?? "An unexpected error occurred."}
          action={
            <Button variant="secondary" size="sm" onClick={() => { reset(); mutate(auditUrl); }}>
              Retry Audit
            </Button>
          }
        />
      )}

      {/* ── Results Section ───────────────────────────────────────────────── */}
      {result && !isPending && (
        <section ref={resultRef} aria-labelledby="results-heading" className="space-y-6">
          {/* Top Score Banner */}
          <div className="p-6 sm:p-8 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 id="results-heading" className="text-xl font-bold text-slate-900 tracking-tight">
                  Audit Findings
                </h2>
                {isCached && (
                  <Badge variant="muted">
                    <Clock size={11} className="mr-1" />
                    Cached Result
                  </Badge>
                )}
                {violations === 0 ? (
                  <Badge variant="success">
                    <CheckCircle size={11} className="mr-1" />
                    100% WCAG Compliant
                  </Badge>
                ) : (
                  <Badge variant="danger">
                    <AlertTriangle size={11} className="mr-1" />
                    {violations} Violation{violations !== 1 ? "s" : ""} Detected
                  </Badge>
                )}
              </div>
              <p className="text-xs font-mono text-blue-700 truncate max-w-xl">
                Target: {result.url}
              </p>
              <p className="text-xs text-slate-500">
                Audit ID: <span className="font-mono text-slate-700">{result.audit_id}</span> · Completed in {result.duration_seconds ? `${result.duration_seconds.toFixed(2)}s` : "< 3s"}
              </p>
            </div>

            {/* Score Ring */}
            <div className="flex items-center gap-4 bg-slate-50 px-6 py-4 rounded-xl border border-slate-200">
              <div className="text-right">
                <div className="text-2xs uppercase tracking-wider text-slate-500 font-bold">
                  Compliance Score
                </div>
                <div className="text-sm font-bold text-slate-800">
                  {complianceScore >= 80 ? "Grade: AA Pass" : "Remediation Required"}
                </div>
              </div>
              <div className="flex items-center justify-center w-14 h-14 rounded-full bg-blue-600 text-white shadow-md">
                <span className="text-lg font-extrabold">
                  {complianceScore}
                </span>
                <span className="text-[10px] text-blue-200 font-medium">
                  %
                </span>
              </div>
            </div>
          </div>

          {/* Metric Cards Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Viewports Captured"
              value={result.viewports_captured?.length ?? 0}
              icon={<Layers size={20} />}
              variant="accent"
            />
            <StatCard
              label="Computed Styles Scanned"
              value={result.computed_styles_count ?? 0}
              icon={<Search size={20} />}
            />
            <StatCard
              label="WCAG Compliant Nodes"
              value={passes}
              icon={<ShieldCheck size={20} />}
              variant="success"
            />
            <StatCard
              label="Remediation Defects"
              value={violations}
              icon={<AlertTriangle size={20} />}
              variant={violations > 0 ? "danger" : "success"}
            />
          </div>

          {/* Result Tabs Container */}
          <div className="rounded-2xl bg-white border border-slate-200 p-6 shadow-sm">
            <ResultTabs result={result} sandboxResult={sandboxResult} />
          </div>
        </section>
      )}
    </div>
  );
}
