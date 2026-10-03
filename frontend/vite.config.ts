import { defineConfig, loadEnv } from "vite";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("..", import.meta.url));
const frontendRoot = fileURLToPath(new URL(".", import.meta.url));
function proxyTarget(mode: string) {
  // Proxy target points to local FastAPI backend
  return process.env.API_PROXY_TARGET
    || loadEnv(mode, frontendRoot, "API_PROXY_").API_PROXY_TARGET
    || loadEnv(mode, projectRoot, "API_PROXY_").API_PROXY_TARGET
    || "http://127.0.0.1:8000";
}
export default defineConfig(({ mode }) => ({
  server: {
    proxy: {
      "/api":
        proxyTarget(mode),
      "^/docs$":
        proxyTarget(mode),
      "/openapi.json":
        proxyTarget(mode),
    },
  },
  build: {
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ["chart.js"],
          animation: ["gsap"],
          vendor: ["jquery"],
        },
      },
    },
  },
}));
