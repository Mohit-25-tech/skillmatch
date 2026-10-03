import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:5182",
    headless: true,
    channel: process.env.CI ? undefined : "chrome",
    viewport: { width: 1440, height: 1100 },
    reducedMotion: "reduce",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        process.platform === "win32"
          ? "..\\.venv\\Scripts\\python.exe ../scripts/run_e2e_api.py"
          : "python ../scripts/run_e2e_api.py",
      url: "http://127.0.0.1:8012/api/v1/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 5182 --strictPort",
      url: "http://127.0.0.1:5182",
      reuseExistingServer: false,
      timeout: 60000,
      env: { API_PROXY_TARGET: "http://127.0.0.1:8012" },
    },
  ],
  reporter: "list",
});
