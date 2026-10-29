import { defineConfig } from "@playwright/test";

// Hermetic UI tests: every backend call and the Binance feed are mocked per test (e2e/fixtures.ts),
// so no Docker, DB, API keys or network are needed. The build uses the same API base a local dev
// build gets by default, so the .next it leaves behind is no different from `npm run build`.
const PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: "list",
  use: { baseURL: `http://localhost:${PORT}`, trace: "retain-on-failure" },
  webServer: {
    command: `npm run build && npx next start -p ${PORT}`,
    url: `http://localhost:${PORT}/login`,
    env: { NEXT_PUBLIC_API_URL: "http://localhost:8000", NEXT_TELEMETRY_DISABLED: "1" },
    reuseExistingServer: false,
    timeout: 240_000,
  },
});
