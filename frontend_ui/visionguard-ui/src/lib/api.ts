const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  redis_connected: boolean;
}

export interface AuditResult {
  audit_id: string;
  url: string;
  timestamp: string;
  duration_seconds: number;
  viewports_captured: string[];
  viewports_failed: Record<string, string>;
  screenshots: Record<string, string>;
  page_title: string;
  computed_styles_count: number;
  computed_styles: ComputedStyle[];
  html_sources: Record<string, string>;
}

export interface AuditResponse {
  audit_id: string;
  status: "processing" | "completed" | "failed";
  url: string;
  message: string;
  result?: AuditResult;
}

export interface ComputedStyle {
  tag: string;
  text: string;
  color: string;
  backgroundColor: string;
  fontSize: string;
  fontWeight: string;
  boundingBox?: { x: number; y: number; width: number; height: number };
  selector: string;
}

export interface SandboxRequest {
  url: string;
  css_patch: string;
  viewport?: string;
}

export interface SandboxResponse {
  success: boolean;
  error?: string;
  original_screenshot?: string;
  patched_screenshot?: string;
  viewport?: string;
}

// ─── API Functions ─────────────────────────────────────────────────────────────

export const api = {
  health: () => request<HealthResponse>("/health"),

  auditUrl: (url: string) =>
    request<AuditResponse>("/audit-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  getAudit: (auditId: string) =>
    request<AuditResponse>(`/audit/${auditId}`),

  verifyPatch: (payload: SandboxRequest) =>
    request<SandboxResponse>("/sandbox/verify-patch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
