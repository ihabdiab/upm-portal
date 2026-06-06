import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxies /api -> backend. In prod, Traefik/Nginx routes /api to the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.UPM_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: { outDir: "dist" },
});
