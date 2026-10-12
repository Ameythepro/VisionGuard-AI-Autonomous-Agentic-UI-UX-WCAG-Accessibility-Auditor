import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FlaskConical, Image as ImageIcon, Check, AlertTriangle, Layers, Eye } from "lucide-react";
import { toast } from "sonner";
import { api, type SandboxResponse, API_BASE } from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspaceStore";

const VIEWPORTS = [
  { value: "desktop_1080p", label: "Desktop 1080p (1920 × 1080)" },
  { value: "desktop_720p",  label: "Desktop 720p (1280 × 720)" },
  { value: "tablet_768",    label: "Tablet (768 × 1024)" },
  { value: "mobile_375",    label: "Mobile (375 × 667)" },
];

const SAMPLE_PATCHES = [
  {
    name: "Darken Low-Contrast Text",
    css: `/* Fix WCAG SC 1.4.3: Ensure text meets 4.5:1 ratio */\np, span, li, a, h1, h2, h3, h4, h5, h6 {\n  color: #0f172a !important;\n}\nbody {\n  background-color: #ffffff !important;\n}`,
  },
  {
    name: "Enlarge Touch Targets (44px)",
    css: `/* Fix WCAG SC 2.5.5: Ensure clickable elements >= 44x44px */\nbutton, a, input[type="button"], input[type="submit"] {\n  min-height: 44px !important;\n  min-width: 44px !important;\n  display: inline-flex !important;\n  align-items: center !important;\n  justify-content: center !important;\n  padding: 8px 16px !important;\n}`,
  },
  {
    name: "Accessible Focus Rings",
    css: `/* Fix WCAG SC 2.4.7: Clear visible keyboard focus */\n*:focus-visible {\n  outline: 3px solid #2563eb !important;\n  outline-offset: 3px !important;\n  border-radius: 4px !important;\n}`,
  },
];

function ScreenshotBox({ path, label, badgeColor }: { path?: string; label: string; badgeColor?: string }) {
  const safePath = path?.replace(/\\/g, '/');
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-800">{label}</p>
        {path && (
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColor ?? "bg-slate-100 text-slate-700 border border-slate-200"}`}>
            Captured
          </span>
        )}
      </div>
      <div className="bg-slate-100 border border-slate-200 rounded-xl h-56 flex items-center justify-center overflow-hidden relative shadow-inner p-2">
        {safePath ? (
          <img 
            src={`${API_BASE}/${safePath}`} 
            alt={label} 
            className="max-h-full max-w-full object-contain rounded" 
          />
        ) : (
          <div className="text-center space-y-1.5 px-4 text-slate-400">
            <ImageIcon size={24} className="mx-auto text-slate-400" />
            <p className="text-xs font-mono">— Waiting for patch injection —</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PatchLabPage() {
  const { patchUrl, setPatchUrl, cssPatch, setCssPatch } = useWorkspaceStore();
  const [viewport, setViewport] = useState("desktop_1080p");
  const [lastResult, setLastResult] = useState<SandboxResponse | null>(null);

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: () =>
      api.verifyPatch({ url: patchUrl.trim(), css_patch: cssPatch.trim(), viewport }),
    onSuccess: (data) => {
      setLastResult(data);
      if (data.success) {
        toast.success("CSS patch applied & verified in sandbox");
      } else {
        toast.error("Patch failed", { description: data.error });
      }
    },
    onError: (err: Error) => {
      toast.error("Request failed", { description: err.message });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!patchUrl.trim() || !cssPatch.trim()) return;
    mutate();
  };

  const canSubmit = patchUrl.trim() && cssPatch.trim() && !isPending;

  return (
    <div className="space-y-8 pb-12">
      {/* ── Page Header ── */}
      <div className="p-6 sm:p-8 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-2">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold uppercase tracking-wider">
          <FlaskConical size={12} className="text-blue-600" />
          <span>Closed-Loop Verification Sandbox</span>
        </div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
          CSS Remediation & Reflection Sandbox
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 max-w-3xl leading-relaxed">
          Inject synthesized CSS patches into a sandboxed Chromium browser instance. VisionGuard rasterizes the page before and after injection to prove zero visual regressions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ── Form Section ── */}
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-5">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Layers size={16} className="text-blue-600" />
            <span>Sandbox Configuration</span>
          </h3>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Target URL to Patch
              </label>
              <input
                type="url"
                placeholder="https://example.com"
                value={patchUrl}
                onChange={(e) => setPatchUrl(e.target.value)}
                disabled={isPending}
                className="w-full px-3.5 py-2.5 text-xs font-mono rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Emulated Viewport
              </label>
              <select
                value={viewport}
                onChange={(e) => setViewport(e.target.value)}
                disabled={isPending}
                className="w-full px-3.5 py-2.5 text-xs rounded-xl bg-slate-50 border border-slate-300 text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white transition-all"
              >
                {VIEWPORTS.map((vp) => (
                  <option key={vp.value} value={vp.value}>
                    {vp.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Quick Sample Patch Buttons */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-700">
                  CSS Remediation Patch
                </label>
                <span className="text-[10px] text-slate-500 font-medium">Quick templates:</span>
              </div>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {SAMPLE_PATCHES.map((sp) => (
                  <button
                    key={sp.name}
                    type="button"
                    onClick={() => setCssPatch(sp.css)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-blue-700 border border-slate-200 transition-colors font-medium"
                  >
                    + {sp.name}
                  </button>
                ))}
              </div>
              <textarea
                value={cssPatch}
                onChange={(e) => setCssPatch(e.target.value)}
                placeholder="/* Paste or write CSS overrides to inject... */"
                disabled={isPending}
                rows={8}
                className="w-full p-3 text-xs font-mono rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white transition-all leading-relaxed"
              />
            </div>

            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isPending ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Executing Sandboxed Browser Injection…</span>
                </>
              ) : (
                <>
                  <FlaskConical size={16} />
                  <span>Apply & Verify in Sandbox</span>
                </>
              )}
            </button>

            {isError && (
              <p className="text-xs text-rose-600 flex items-center gap-1.5">
                <AlertTriangle size={14} />
                <span>{(error as Error)?.message}</span>
              </p>
            )}
          </form>
        </div>

        {/* ── Results & Before/After Comparison ── */}
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-slate-200 pb-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Eye size={16} className="text-blue-600" />
              <span>Visual Comparison (Rasterized)</span>
            </h3>

            {lastResult && (
              <div className="flex items-center gap-2">
                {lastResult.success ? (
                  <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold flex items-center gap-1">
                    <Check size={12} /> Verified Pass
                  </span>
                ) : (
                  <span className="px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 text-xs font-semibold flex items-center gap-1">
                    <AlertTriangle size={12} /> Failed
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <ScreenshotBox
              path={lastResult?.original_screenshot}
              label="Original State (Before Patch)"
              badgeColor="bg-slate-100 text-slate-700 border border-slate-200"
            />
            <ScreenshotBox
              path={lastResult?.patched_screenshot}
              label="Patched State (After Injection)"
              badgeColor="bg-emerald-50 text-emerald-700 border border-emerald-200"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
