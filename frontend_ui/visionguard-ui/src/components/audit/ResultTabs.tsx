import { useState } from "react";
import { Image, AlertTriangle, LayoutList, FileJson } from "lucide-react";
import { cn } from "@/lib/utils";
import { ViolationList } from "./ViolationList";
import { StylesTable } from "./StylesTable";
import { EmptyState } from "@/components/ui/States";
import type { AuditResult, SandboxResponse } from "@/lib/api";
import {
  getContrastRatioFromRgb,
  isLargeText,
  wcagLevel,
} from "@/lib/wcag";

const TABS = [
  { id: "screenshots", label: "Screenshots", icon: Image },
  { id: "violations",  label: "Violations",  icon: AlertTriangle },
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
                <div className="bg-bg-subtle border border-border rounded-lg h-40 flex items-center justify-center">
                  <div className="text-center space-y-1 px-4">
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
                <div className="bg-bg-subtle border border-border rounded-lg h-48 flex items-center justify-center">
                  <div className="text-center space-y-1 px-4">
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
                  ? "text-text-primary border-b-2 border-accent -mb-px"
                  : "text-text-secondary hover:text-text-primary"
              )}
            >
              <Icon size={14} />
              {label}
              {id === "violations" && violationCount > 0 && (
                <span className="ml-0.5 bg-danger text-white text-2xs font-semibold rounded-sm px-1 py-0.5 leading-none">
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
