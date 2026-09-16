import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { Layout } from "@/components/layout/Layout";
import AuditPage from "@/pages/AuditPage";
import PatchLabPage from "@/pages/PatchLabPage";
import WcagGuidePage from "@/pages/WcagGuidePage";

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
            <Route path="/" element={<AuditPage />} />
            <Route path="/patch-lab" element={<PatchLabPage />} />
            <Route path="/wcag" element={<WcagGuidePage />} />
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
