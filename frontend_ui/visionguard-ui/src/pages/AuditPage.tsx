import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search, Clock, Globe, Layers, AlertTriangle, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
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
        // Scroll to results
        setTimeout(() => {
          resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);
        toast.success("Audit complete", {
          description: `${data.result.viewports_captured.length} viewports captured`,
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
  const passes = result ? (result.computed_styles?.length ?? 0) - violations : 0;

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* ── URL input section ─────────────────────────────────────────────── */}
      <section aria-labelledby="audit-heading">
        <h2 id="audit-heading" className="text-lg font-semibold text-text-primary mb-1">
          Run an audit
        </h2>
        <p className="text-sm text-text-secondary mb-4">
          Enter any publicly accessible URL to analyse for WCAG 2.1 AA accessibility violations.
        </p>

        <form onSubmit={handleSubmit} className="flex gap-2" noValidate>
          <div className="flex-1">
            <Input
              type="url"
              placeholder="https://example.com"
              value={auditUrl}
              onChange={(e) => setAuditUrl(e.target.value)}
              leftIcon={<Globe size={15} />}
              aria-label="URL to audit"
              disabled={isPending}
            />
          </div>
          <Button type="submit" loading={isPending} disabled={!auditUrl.trim()}>
            <Search size={15} />
            {isPending ? "Auditing…" : "Audit"}
          </Button>
        </form>

        {/* Quick examples */}
        <div className="flex flex-wrap gap-2 mt-3">
          <span className="text-xs text-text-tertiary pt-0.5">Try:</span>
          {["https://example.com", "https://httpbin.org"].map((eg) => (
            <button
              key={eg}
              type="button"
              onClick={() => setAuditUrl(eg)}
              className="text-xs text-accent hover:text-accent-hover transition-colors duration-150 font-mono"
            >
              {eg}
            </button>
          ))}
        </div>
      </section>

      {/* ── Loading skeleton ──────────────────────────────────────────────── */}
      {isPending && (
        <section aria-live="polite" aria-busy="true">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" aria-hidden="true" />
            <p className="text-sm text-text-secondary">
              Launching browser · capturing screenshots · analysing styles…
            </p>
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
              Retry
            </Button>
          }
        />
      )}

      {/* ── Results ───────────────────────────────────────────────────────── */}
      {result && !isPending && (
        <section ref={resultRef} aria-labelledby="results-heading" className="space-y-5 animate-fade-in">
          {/* Results header */}
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 id="results-heading" className="text-base font-semibold text-text-primary">
                  Results
                </h2>
                {isCached && (
                  <Badge variant="muted">
                    <Clock size={10} />
                    Cached
                  </Badge>
                )}
                {violations === 0 ? (
                  <Badge variant="success">
                    <CheckCircle size={10} />
                    No violations
                  </Badge>
                ) : (
                  <Badge variant="danger">
                    <AlertTriangle size={10} />
                    {violations} violation{violations !== 1 ? "s" : ""}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-text-secondary mt-0.5 font-mono truncate max-w-lg">
                {result.url}
              </p>
            </div>
            <p className="text-xs text-text-tertiary pt-1">
              ID: <span className="font-mono">{result.audit_id}</span>
            </p>
          </div>

          {/* Stat cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard
              label="Viewports"
              value={result.viewports_captured?.length ?? 0}
              icon={<Layers />}
              variant="accent"
            />
            <StatCard
              label="Elements scanned"
              value={result.computed_styles_count ?? 0}
              icon={<Search />}
            />
            <StatCard
              label="Passed"
              value={passes}
              icon={<CheckCircle />}
              variant={passes > 0 ? "success" : "default"}
            />
            <StatCard
              label="Violations"
              value={violations}
              icon={<AlertTriangle />}
              variant={violations > 0 ? "danger" : "success"}
            />
          </div>

          {/* Separator */}
          <div className="border-t border-border" />

          {/* Result tabs */}
          <ResultTabs result={result} sandboxResult={sandboxResult} />
        </section>
      )}
    </div>
  );
}
