import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";
const nextConfig: NextConfig = {};
export default withSentryConfig(nextConfig, {
  org: "nirmalhk7",
  project: "sueperman-frontend",
  silent: !process.env.CI,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  telemetry: false,
  sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
});
