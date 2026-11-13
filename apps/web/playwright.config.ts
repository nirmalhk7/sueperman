import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "*.e2e.ts",
  workers: 1,
  use: {
    channel: "chromium",
    baseURL: process.env.WEB_URL || "http://localhost:3000",
    video: "on",
    trace: "retain-on-failure",
  },
  reporter: [["list"]],
});
