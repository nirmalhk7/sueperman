# Sentry setup and live verification

Approved organization `nirmalhk7`, team `personal`:

- `sueperman-server` — Python/FastAPI
- `sueperman-frontend` — Next.js

Sentry CLI 0.49.0 authenticated through the user's one-time handoff. Installer SHA-256 was verified before execution. Handoff/setup codes and authentication credentials are not stored in repository files or this report. CLI credentials remain CLI-managed.

## Configuration

Backend `SENTRY_DSN` is stored only in ignored root `.env`. Frontend server and public client DSNs are in ignored `apps/web/.env.local`. A public DSN routes telemetry; it is not an API authentication token. File permissions are owner-only. No model/API credential is exposed through `NEXT_PUBLIC_`.

SDKs: sentry-sdk 2.75.0 and @sentry/nextjs 11.12.0, checked against PyPI/npm during setup. FastAPI integrates Starlette/FastAPI/HTTPX. Next.js uses instrumentation-client.ts, server/edge init, onRequestError and global-error.tsx.

- Errors retain type, source location and source structure. Exception messages are redacted unless they match the fixed verification-message format. Source string literals, local variables, request data, user fields and breadcrumbs are stripped.
- Trace sampling: 100% in development, 10% in production. Python uses `SENTRY_ENVIRONMENT`; frontend uses `NODE_ENV`. Release is `sueperman@0.1.0`.
- Python transaction and JavaScript streamed-span filters remove raw attributes and URL names. HTTP bodies, headers, cookies, query values and AI inputs/outputs are disabled at collection.
- Logs allow only fixed operational/verification messages; arbitrary attributes and raw application logs are not forwarded.
- Browser Replay masks all text/inputs and blocks media; detailed network bodies are disabled. Samples 10% of sessions and 100% of error sessions. Only validated replay correlation IDs survive event filtering.
- Source-map debug IDs and sanitized frame locations are preserved. Source-map upload is configured through `SENTRY_AUTH_TOKEN` at build time; never put this auth token in a public variable.

## Actual live results

Temporary errors were triggered through normal `make dev` startup: an actual FastAPI route raised RuntimeError, and an actual browser button threw Error. They were not standalone SDK capture scripts.

- Backend issue: **SUEPERMAN-SERVER-1**, `RuntimeError: Sueperman Sentry verification 1794596496 backend`, https://nirmalhk7.sentry.io/issues/7846942072/
- Initial frontend issue: **SUEPERMAN-FRONTEND-1**, https://nirmalhk7.sentry.io/issues/7846942122/ — captured before source-map linking.
- Source-mapped frontend verification: **SUEPERMAN-FRONTEND-2**, `Error: Sueperman Sentry verification 1794596496 frontend`, https://nirmalhk7.sentry.io/issues/7846950178/
- Backend trace: `65d94c9ccc014552a0352fd216b9ecd7`.
- Browser trace: `46165d64055a4f339c9862803ac6f533`.
- Both projects returned the corresponding verification log through `sentry log list`.
- Stored replay: `948d15a1001f44e49bbd6eeac7c44e34`; 2 segments, 63 rrweb events, about 6 seconds. Downloaded replay was checked: visible page text was masked, and user identity/IP fields were null.

Stack quality: backend application frames had source context. Initial browser app frame lacked context. Uploaded the temporary page's JS/source-map pair with authenticated CLI to the approved frontend project and triggered a new event. The new frame mapped to original `app/sentry-verification/page.tsx`, line 8, with source context. Third-party React frames still lacked uploaded library context; application frames were readable.

Temporary route/page and their temporary browser checks were removed after verification. Test issues remain open; resolving them is a separate user decision. No issue comments or notifications were posted.

## Production next step

No production service has been deployed. The agreed hosting direction remains DigitalOcean App Platform after its credentials/configuration are available. Set backend `SENTRY_ENVIRONMENT=production`, backend/frontend DSNs and the release in that environment. Configure a secret build-time `SENTRY_AUTH_TOKEN` so withSentryConfig emits/uploads production source maps; this path is prepared but not yet proven on a deployed production build. Trigger a new production error after deployment and verify its frames. Local verification does not claim production success.

## Verification and regressions

- Privacy tests observed failures before implementation: dropped exceptions, leaked event/span attributes, discarded debug IDs and discarded replay correlation.
- Actual Python SDK transport test caught string-literal values in source context; source literal redaction repaired it while retaining readable locations.
- Live SDK verification caught JavaScript v11's default streamed-span API and replay's required correlation tag. Added matching tests and filters instead of claiming configuration alone proved success.
- Regression commands/results are recorded in implementation-log.md and final monitoring check logs.
