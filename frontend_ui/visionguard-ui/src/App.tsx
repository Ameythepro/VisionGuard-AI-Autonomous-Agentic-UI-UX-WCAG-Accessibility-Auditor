import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { Layout } from "@/components/layout/Layout";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import AuditPage from "@/pages/AuditPage";
import PatchLabPage from "@/pages/PatchLabPage";
import WcagGuidePage from "@/pages/WcagGuidePage";
import ScreenshotLabPage from "@/pages/ScreenshotLabPage";


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60 * 5, // 5 minutes
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<ErrorBoundary><AuditPage /></ErrorBoundary>} />
            <Route path="/screenshot-lab" element={<ErrorBoundary><ScreenshotLabPage /></ErrorBoundary>} />
            <Route path="/patch-lab" element={<ErrorBoundary><PatchLabPage /></ErrorBoundary>} />
            <Route path="/wcag" element={<ErrorBoundary><WcagGuidePage /></ErrorBoundary>} />
          </Route>
        </Routes>
      </BrowserRouter>

      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--color-bg-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-primary)",
            fontSize: "0.875rem",
            borderRadius: "8px",
          },
        }}
      />
    </QueryClientProvider>
  );
}
