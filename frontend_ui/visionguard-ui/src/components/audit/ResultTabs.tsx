import { useState } from "react";
import { Image, AlertTriangle, LayoutList, FileJson, Wand2, FlaskConical, Check } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { ViolationList } from "./ViolationList";
import { StylesTable } from "./StylesTable";
import { EmptyState } from "@/components/ui/States";
import { api, API_BASE, type AuditResult, type SandboxResponse } from "@/lib/api";
import {
  getContrastRatioFromRgb,
  isLargeText,
  wcagLevel,
} from "@/lib/wcag";

const TABS = [
  { id: "screenshots", label: "Screenshots", icon: Image },
  { id: "violations",  label: "Violations",  icon: AlertTriangle },
  { id: "fixes",       label: "AI Fixes",    icon: Wand2 },
  { id: "styles",      label: "Computed styles", icon: LayoutList },
  { id: "raw",         label: "Raw JSON",    icon: FileJson },
] as const;

type TabId = (typeof TABS)[number]["id"];

interface ResultTabsProps {
  result: AuditResult;
  sandboxResult?: SandboxResponse | null;
}

function ScreenshotsTab({
  result,
  sandboxResult,
}: {
  result: AuditResult;
  sandboxResult?: SandboxResponse | null;
}) {
  const screenshots = Object.entries(result.screenshots ?? {});

  return (
    <div className="space-y-6">
      {/* Viewport screenshots */}
      {screenshots.length === 0 ? (
        <EmptyState
          icon={<Image />}
          title="No screenshots"
          description="Screenshots are saved locally on the server. Ensure the audit completed successfully."
        />
      ) : (
        <div>
          <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">
            Captured viewports
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {screenshots.map(([name, path]) => (
              <div key={name} className="space-y-2">
                <p className="text-xs font-medium text-text-secondary capitalize">
                  {name.replace(/_/g, " ")}
                </p>
                <div className="bg-bg-subtle border border-border rounded-lg h-40 flex items-center justify-center overflow-hidden relative">
                  <img
                    src={`${API_BASE}/${path}`}
                    alt={`${name} screenshot`}
                    className="w-full h-full object-cover object-top"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                      e.currentTarget.nextElementSibling?.classList.remove('hidden');
                    }}
                  />
                  <div className="text-center space-y-1 px-4 hidden absolute inset-0 flex flex-col items-center justify-center bg-bg-subtle">
                    <Image size={20} className="text-text-tertiary mx-auto" />
                    <p className="text-xs text-text-tertiary font-mono break-all">{path}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Before/After comparison */}
      {sandboxResult && (
        <div>
          <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">
            Before / After patch comparison
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { label: "Before (original)", path: sandboxResult.original_screenshot },
              { label: "After (patched)",   path: sandboxResult.patched_screenshot },
            ].map(({ label, path }) => (
              <div key={label} className="space-y-2">
                <p className="text-xs font-medium text-text-secondary">{label}</p>
                <div className="bg-bg-subtle border border-border rounded-lg h-48 flex items-center justify-center overflow-hidden relative">
                  {path ? (
                    <img
                      src={`${API_BASE}/${path}`}
                      alt={`${label} screenshot`}
                      className="w-full h-full object-cover object-top"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                        e.currentTarget.nextElementSibling?.classList.remove('hidden');
                      }}
                    />
                  ) : null}
                  <div className={cn("text-center space-y-1 px-4 absolute inset-0 flex flex-col items-center justify-center bg-bg-subtle", path ? "hidden" : "")}>
                    <Image size={20} className="text-text-tertiary mx-auto" />
                    <p className="text-xs text-text-tertiary font-mono break-all">{path ?? "—"}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Failed viewports */}
      {Object.keys(result.viewports_failed ?? {}).length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">
            Failed viewports
          </h3>
          <div className="space-y-1.5">
            {Object.entries(result.viewports_failed).map(([vp, err]) => (
              <div key={vp} className="flex gap-2 text-xs">
                <span className="font-mono text-text-secondary">{vp}:</span>
                <span className="text-danger">{err}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AIFixesTab({ result }: { result: AuditResult }) {
  const [sandboxResult, setSandboxResult] = useState<SandboxResponse | null>(null);
  
  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      api.verifyPatch({ url: result.url, css_patch: result.ai_combined_patch || "", viewport: "desktop_1080p" }),
    onSuccess: (data) => {
      setSandboxResult(data);
      if (data.success) {
        toast.success("All AI fixes applied successfully");
      } else {
        toast.error("Patch failed", { description: data.error });
      }
    },
    onError: (err: Error) => {
      toast.error("Request failed", { description: err.message });
    },
  });

  if (!result.ai_patches || result.ai_patches.length === 0) {
    return (
      <EmptyState
        icon={<Wand2 />}
        title="No AI Fixes Available"
        description="The AI did not identify any automatic fixes for this page, or no violations were found."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Generated CSS Patches</h3>
          <p className="text-xs text-text-secondary">The AI has generated {result.ai_patches.length} fixes for the detected contrast issues.</p>
        </div>
        <Button onClick={() => mutate()} loading={isPending} disabled={!result.ai_combined_patch}>
          <FlaskConical size={14} className="mr-1.5" />
          Apply All Fixes Now
        </Button>
      </div>

      {sandboxResult && (
        <div className="space-y-4 animate-fade-in border-b border-border pb-6">
          <div className="flex items-center gap-2 mb-2">
            {sandboxResult.success ? (
              <>
                <div className="w-5 h-5 rounded-full bg-success-subtle border border-success-muted flex items-center justify-center">
                  <Check size={12} className="text-success" />
                </div>
                <span className="text-sm font-medium text-success">Live Preview Generated</span>
              </>
            ) : (
              <>
                <div className="w-5 h-5 rounded-full bg-danger-subtle border border-danger-muted flex items-center justify-center">
                  <AlertTriangle size={12} className="text-danger" />
                </div>
                <span className="text-sm font-medium text-danger">Live Preview Failed: {sandboxResult.error}</span>
              </>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { label: "Before (original)", path: sandboxResult.original_screenshot },
              { label: "After (patched)",   path: sandboxResult.patched_screenshot },
            ].map(({ label, path }) => (
              <div key={label} className="space-y-2">
                <p className="text-xs font-medium text-text-secondary">{label}</p>
                <div className="bg-bg-subtle border border-border rounded-lg h-56 flex items-center justify-center overflow-hidden relative">
                  {path ? (
                    <img src={`${API_BASE}/${path}`} alt={`${label} screenshot`} className="w-full h-full object-contain" />
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        {result.ai_patches.map((patch, i) => (
          <div key={i} className="border border-border rounded-lg overflow-hidden">
            <div className="bg-bg-subtle px-4 py-2 border-b border-border">
              <code className="text-xs font-semibold text-accent">{patch.selector}</code>
              <p className="text-xs text-text-secondary mt-1">{patch.description}</p>
            </div>
            <pre className="p-4 text-xs font-mono bg-bg-surface text-text-primary overflow-x-auto">
              <code>{patch.css}</code>
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ResultTabs({ result, sandboxResult }: ResultTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>("violations");

  const violationCount = result.computed_styles?.filter((el) => {
    const ratio = getContrastRatioFromRgb(el.color, el.backgroundColor);
    const large = isLargeText(el.fontSize, el.fontWeight);
    return ratio !== null && wcagLevel(ratio, large) === "FAIL";
  }).length ?? 0;

  return (
    <div>
      {/* Tab list */}
      <div
        className="flex border-b border-border gap-0 overflow-x-auto"
        role="tablist"
        aria-label="Audit result sections"
      >
        {TABS.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`tabpanel-${id}`}
              id={`tab-${id}`}
              onClick={() => setActiveTab(id)}
              className={cn(
                "relative flex items-center gap-1.5 px-4 h-10 text-sm font-medium",
                "whitespace-nowrap transition-colors duration-150 shrink-0",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-[-2px]",
                isActive
                  ? "text-blue-700 bg-blue-50/80 border-b-2 border-blue-600 font-bold -mb-px"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              )}
            >
              <Icon size={14} className={isActive ? "text-blue-600" : "text-slate-500"} />
              {label}
              {id === "violations" && violationCount > 0 && (
                <span className="ml-1.5 bg-rose-600 text-white text-[10px] font-bold rounded-full px-1.5 py-0.5 leading-none">
                  {violationCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab panels */}
      <div className="pt-5">
        <div
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
          className="animate-fade-in"
        >
          {activeTab === "screenshots" && (
            <ScreenshotsTab result={result} sandboxResult={sandboxResult} />
          )}
          {activeTab === "violations" && (
            <ViolationList styles={result.computed_styles ?? []} />
          )}
          {activeTab === "fixes" && (
            <AIFixesTab result={result} />
          )}
          {activeTab === "styles" && (
            <StylesTable styles={result.computed_styles ?? []} />
          )}
          {activeTab === "raw" && (
            <div>
              <div className="flex justify-end mb-2">
                <button
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(result, null, 2)], {
                      type: "application/json",
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `visionguard-audit-${result.audit_id}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="text-xs text-accent hover:text-accent-hover transition-colors duration-150"
                >
                  Download JSON
                </button>
              </div>
              <pre className="bg-bg-subtle border border-border rounded-lg p-4 text-xs font-mono text-text-primary overflow-auto max-h-[480px] leading-relaxed">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

