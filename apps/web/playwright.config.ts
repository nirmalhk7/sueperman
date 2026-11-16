import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "*.e2e.ts",
  workers: 1,
  use: {
    channel: "chromium",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : {},
    baseURL: process.env.WEB_URL || "http://localhost:3000",
    video: "on",
    trace: "retain-on-failure",
  },
  reporter: [["list"]],
});
