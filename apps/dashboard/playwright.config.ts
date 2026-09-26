// Playwright smoke tests for Signal Command (e2e/). They need the local system running:
//   the API with dev OTP codes on  (AUTH_DEV_ECHO_OTP=1, the e2e email in ADMIN_EMAILS)
//   and the dashboard (pnpm dev:dashboard). `make e2e-dashboard` starts both for you.
// Two projects: a desktop browser and a 375 px phone, so every screen is checked at both widths.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  globalSetup: "./e2e/global-setup.ts",
  timeout: 60_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.DASHBOARD_URL ?? "http://localhost:3001",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "phone", use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 812 }, isMobile: false } },
  ],
});
