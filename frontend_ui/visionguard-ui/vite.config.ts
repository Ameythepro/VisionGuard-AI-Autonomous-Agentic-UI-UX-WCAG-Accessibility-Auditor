import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to FastAPI during development
      "/audit-url":        "http://localhost:8001",
      "/audit":            "http://localhost:8001",
      "/sandbox":          "http://localhost:8001",
      "/health":           "http://localhost:8001",
      "/screenshot":       "http://localhost:8001",
      "/temp_screenshots": "http://localhost:8001",
      "/status":           "http://localhost:8001",
    },
  },
});
