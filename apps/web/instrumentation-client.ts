import * as Sentry from "@sentry/nextjs";
import {
  dataCollection,
  sanitizeEvent,
  sanitizeTransaction,
  sanitizeLog,
  sanitizeSpan,
} from "./lib/telemetry";
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment:
    process.env.NODE_ENV === "production" ? "production" : "development",
  release: "sueperman@0.1.0",
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
  dataCollection,
  beforeSend: sanitizeEvent,
  beforeSendTransaction: sanitizeTransaction,
  beforeSendLog: sanitizeLog,
  beforeSendSpan: Sentry.withStreamedSpan(sanitizeSpan),
  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      maskAllInputs: true,
      blockAllMedia: true,
      networkDetailAllowUrls: [],
      networkCaptureBodies: false,
    }),
  ],
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
