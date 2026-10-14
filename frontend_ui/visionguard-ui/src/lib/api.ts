const isBrowser = typeof window !== "undefined";
const isLocalhost = isBrowser && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");

export const API_BASE = 
  import.meta.env.VITE_API_URL || 
  (isLocalhost ? "http://localhost:8001" : "https://visionguard-ai-zmtz.onrender.com");

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
  ai_patches?: Array<{
    selector: string;
    description: string;
    css: string;
  }>;
  ai_combined_patch?: string;
  ai_analysis?: any;
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

export interface ScreenshotAnalysisResponse {
  analysis_id: string;
  timestamp: string;
  overall_score: number;
  summary: string;
  violations: Array<{
    id: string;
    type: string;
    severity: string;
    wcag_criterion: string;
    description: string;
    element_description: string;
    suggestion: string;
  }>;
  positive_findings: string[];
  design_observations: string[];
  original_screenshot: string;
  error?: string;
}

export interface ScreenshotFixResponse {
  html?: string;
  fixed_screenshot_path?: string;
  error?: string;
  warning?: string;
  message?: string;
}

export interface ScreenshotChatResponse {
  response: string;
  analysis_id: string;
}

export interface ScreenshotChatHistory {
  analysis_id: string;
  messages: Array<{
    role: string;
    content: string;
    timestamp: string;
  }>;
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

  analyzeScreenshot: async (file: File, prompt?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (prompt) {
      formData.append("prompt", prompt);
    }
    const res = await fetch(`${API_BASE}/screenshot/analyze`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }
    return res.json() as Promise<ScreenshotAnalysisResponse>;
  },

  generateFix: async (analysisId: string, prompt?: string) => {
    const formData = new FormData();
    formData.append("analysis_id", analysisId);
    if (prompt) {
      formData.append("prompt", prompt);
    }
    const res = await fetch(`${API_BASE}/screenshot/generate-fix`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }
    return res.json() as Promise<ScreenshotFixResponse>;
  },

  refineCode: async (analysisId: string, prompt: string) => {
    const formData = new FormData();
    formData.append("analysis_id", analysisId);
    formData.append("prompt", prompt);
    const res = await fetch(`${API_BASE}/screenshot/refine`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }
    return res.json() as Promise<ScreenshotFixResponse>;
  },

  chatScreenshot: async (analysisId: string, message: string) => {
    const formData = new FormData();
    formData.append("analysis_id", analysisId);
    formData.append("message", message);
    const res = await fetch(`${API_BASE}/screenshot/chat`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }
    return res.json() as Promise<ScreenshotChatResponse>;
  },
};

