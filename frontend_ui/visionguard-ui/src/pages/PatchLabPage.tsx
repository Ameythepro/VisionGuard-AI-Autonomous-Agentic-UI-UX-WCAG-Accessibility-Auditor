import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FlaskConical, Image, Check, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api, type SandboxResponse, API_BASE } from "@/lib/api";

const VIEWPORTS = [
  { value: "desktop_1080p", label: "Desktop 1080p" },
  { value: "desktop_720p",  label: "Desktop 720p" },
  { value: "tablet_768",    label: "Tablet (768px)" },
  { value: "mobile_375",    label: "Mobile (375px)" },
];

const CSS_PLACEHOLDER = `/* Example: fix low-contrast grey text */
p, span {
  color: #1a1a1a !important;
}

a {
  color: #1d4ed8 !important;
}`;

function ScreenshotBox({ path, label }: { path?: string; label: string }) {
  const safePath = path?.replace(/\\/g, '/');
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-text-secondary">{label}</p>
      <div className="bg-bg-subtle border border-border rounded-lg h-52 flex items-center justify-center overflow-hidden">
        {safePath ? (
          <img src={`${API_BASE}/${safePath}`} alt={label} className="max-h-full max-w-full object-contain" />
        ) : (
          <div className="text-center space-y-1.5 px-4">
            <Image size={22} className="text-text-tertiary mx-auto" />
            <p className="text-xs text-text-tertiary font-mono break-all">—</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PatchLabPage() {
  const [patchUrl, setPatchUrl] = useState("");
  const [cssPatch, setCssPatch] = useState("");
  const [viewport, setViewport] = useState("desktop_1080p");
  const [lastResult, setLastResult] = useState<SandboxResponse | null>(null);

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: () =>
      api.verifyPatch({ url: patchUrl.trim(), css_patch: cssPatch.trim(), viewport }),
    onSuccess: (data) => {
      setLastResult(data);
      if (data.success) {
        toast.success("Patch applied successfully");
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
    if (!patchUrl.trim()) return;
    if (!cssPatch.trim()) return;
    mutate();
  };

  const canSubmit = patchUrl.trim() && cssPatch.trim() && !isPending;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-lg font-semibold text-text-primary mb-1">CSS Patch Lab</h2>
        <p className="text-sm text-text-secondary">
          Inject a CSS patch into a sandboxed Chromium browser and capture before/after
          screenshots to verify fixes — this powers the AI reflection loop.
        </p>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-6">
        {/* ── Form ─────────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Input
            label="Target URL"
            type="url"
            placeholder="https://example.com"
            value={patchUrl}
            onChange={(e) => setPatchUrl(e.target.value)}
            disabled={isPending}
            hint="The URL to inject the CSS patch into"
          />

          <Select
            label="Viewport"
            options={VIEWPORTS}
            value={viewport}
            onChange={(e) => setViewport(e.target.value)}
            disabled={isPending}
          />

          <Textarea
            label="CSS patch"
            value={cssPatch}
            onChange={(e) => setCssPatch(e.target.value)}
            placeholder={CSS_PLACEHOLDER}
            disabled={isPending}
            hint="This CSS is injected via a <style> tag into the live page"
            className="min-h-[200px] lg:min-h-[280px]"
          />

          <Button
            type="submit"
            loading={isPending}
            disabled={!canSubmit}
            className="w-full"
          >
            <FlaskConical size={15} />
            {isPending ? "Injecting patch…" : "Apply & verify patch"}
          </Button>

          {isError && (
            <p className="text-sm text-danger flex items-center gap-1.5">
              <AlertTriangle size={14} />
              {(error as Error)?.message}
            </p>
          )}
        </form>

        {/* ── Result panel ─────────────────────────────────────────────── */}
        <div className="space-y-4">
          {/* Status */}
          {lastResult && (
            <div className="flex items-center gap-2">
              {lastResult.success ? (
                <>
                  <div className="w-5 h-5 rounded-full bg-success-subtle border border-success-muted flex items-center justify-center">
                    <Check size={12} className="text-success" />
                  </div>
                  <Badge variant="success">Patch applied</Badge>
                </>
              ) : (
                <>
                  <div className="w-5 h-5 rounded-full bg-danger-subtle border border-danger-muted flex items-center justify-center">
                    <AlertTriangle size={12} className="text-danger" />
                  </div>
                  <Badge variant="danger">Patch failed</Badge>
                  {lastResult.error && (
                    <span className="text-xs text-text-secondary">{lastResult.error}</span>
                  )}
                </>
              )}
            </div>
          )}

          {/* Before/After screenshots */}
          <ScreenshotBox
            path={lastResult?.original_screenshot}
            label="Before (original)"
          />
          <ScreenshotBox
            path={lastResult?.patched_screenshot}
            label="After (patched)"
          />

          {!lastResult && !isPending && (
            <div className="h-52 bg-bg-subtle border border-dashed border-border rounded-lg flex items-center justify-center">
              <p className="text-sm text-text-tertiary text-center px-4">
                Screenshots will appear here after you apply a patch
              </p>
            </div>
          )}

          {isPending && (
            <div className="h-52 bg-bg-subtle border border-border rounded-lg flex items-center justify-center">
              <div className="text-center space-y-2">
                <div className="w-2 h-2 bg-accent rounded-full animate-pulse mx-auto" />
                <p className="text-sm text-text-secondary">Launching sandboxed browser…</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
