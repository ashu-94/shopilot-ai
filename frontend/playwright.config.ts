import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 300000,
  reporter: [
    ["list"],
    ["json", { outputFile: "../verification/accessibility.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:4173",
    reducedMotion: "reduce",
    screenshot: "only-on-failure",
  },
  webServer: process.env.E2E_EXTERNAL_SERVERS
    ? undefined
    : [
        {
          command:
            process.platform === "win32"
              ? ".venv\\Scripts\\python.exe -m scripts.test_server"
              : ".venv/bin/python -m scripts.test_server",
          cwd: "..",
          url: "http://127.0.0.1:8123/health/live",
          timeout: 60000,
          reuseExistingServer: false,
        },
        {
          command: "npm run preview -- --port 4173",
          url: "http://127.0.0.1:4173",
          env: { BACKEND_URL: "http://127.0.0.1:8123" },
          timeout: 60000,
          reuseExistingServer: false,
        },
      ],
});
