# Sueperman — Your consumer-rights agent

Fixture-first consumer remedy discovery. Import purchases, compare exact product identifiers with official recall evidence, inspect exclusions, review a local remedy draft, and export Markdown. No external claim submission, money movement or legal advice.

## Run locally

Prerequisites: Node.js 20.19+ (verified with 24.1.0), pnpm (verified with 11.25.0), uv, and network access for first dependency/runtime installation. Python 3.12 is installed automatically by uv when needed. On macOS, prerequisites can be installed with `brew install node pnpm uv`.

From repository root:

```sh
cp .env.example .env
make setup
make dev
```

Open http://localhost:3000. API health: http://localhost:8000/api/health. API docs: http://localhost:8000/docs. Click **Try demo data**, then **Check my purchases**.

If another app owns 3000, keep it running and use:

```sh
make dev WEB_PORT=3001
```

Open http://localhost:3001. This also configures CORS for that origin. Use `WEB_PORT=3001` for smoke and E2E commands below. Stop dev with Ctrl+C. Restart backend after Python changes. The app binds to loopback and has no account system; do not expose this local demo as a shared production service.

## Verify

Run these while both apps are running:

```sh
make seed
make demo
make demo
make test
make lint
make typecheck
make smoke
make e2e
make build
```

`make demo` asserts counts and prints actual JSON, failing nonzero on unexpected outcomes. Expected fixture results: five products; one matched recall, one rejected near-match, one missing-model review, one product without recall, one prominently simulated settlement; exactly one real-recall packet. Imports and run triggers are idempotent. Demo reset preserves non-demo imported records. **Try demo data** selects only five demo rows.

`make test` runs pytest plus frontend unit checks. Playwright verifies evidence, negative cases, missing model, simulation, local approval and downloaded Markdown; it records video and screenshots under `apps/web/test-results/`. Stable delivery copies are in `output/playwright/`. See `docs/implementation-log.md` for actual commands and outcomes.

## Live providers

All provider flags default off. Offline CSV/rules/recorded CPSC require no paid keys.

- CPSC: set `CPSC_LIVE_ENABLED=true` in `.env`, restart backend, choose **Live APIs with labeled fallback** under demo controls. The production adapter has a recorded live proof in `docs/evidence/live-cpsc.json`. Run `PYTHONPATH=services/api services/api/.venv/bin/python scripts/live_cpsc_check.py` for a fresh public read. The normalizer supports notice 26-792 explicitly; changed or unsupported notices require manual review.
- Bright Data: set `BRIGHTDATA_ENABLED=true` and server-only `BRIGHTDATA_API_TOKEN`. Uses Python MCP stdio with `npx @brightdata/mcp`, exposing only `search_engine` and `scrape_as_markdown`. First npx startup may exceed the bounded timeout; preinstall/warm the official package if needed. Only supported CPSC-linked public manufacturer pages are researched. Failure retains CPSC facts and marks partial.
- Gemini: set `GEMINI_ENABLED=true` and server-only `GEMINI_API_KEY`. Upload PNG/JPEG/PDF; default remains `gemini-2.5-flash-lite` per SPEC. New accounts may receive 404 for that retired model; this account uses `GEMINI_MODEL=gemini-3.5-flash-lite`. Live PNG/PDF extraction is proven in `docs/evidence/p1-gemini-api-live.json`. Review and explicitly confirm brand/model/UPC in the purchase table before matching. Full dates, lengths and extra fields are validated locally after structural JSON output. Generation is capped at 1,024 tokens, SDK retries disabled, and duplicate imports reuse the prior extraction. CSV remains available.
- OpenAI decision role (System 1): set `OPENAI_ENABLED=true` and server-only `OPENAI_API_KEY`. `OPENAI_DECISION_MODEL` defaults to `gpt-6-luna` and is configurable. Responses API receives only sanitized hard-gate status/missing-condition names, uses a strict four-choice JSON schema and `store:false`, and exposes no tools. Refusals, malformed output and failures fall back to rules; model output cannot override hard gates. One live request selected `request_user_info`; see `docs/evidence/p1-model-live.json`. `OPENAI_MAX_CALLS_PER_RUN=3` bounds cost; remaining candidates use labeled deterministic rules. Details show selected/proposed actions and guardrail overrides.
- Sentry: backend `SENTRY_DSN` and frontend `apps/web/.env.local` configure separate projects. Real backend/browser errors, traces, logs and masked replay were received; application source frames were verified readable. See `docs/sentry-setup.md` for evidence, strict privacy filters and production/source-map requirements.

- Settlements: `SETTLEMENT_LIVE_ENABLED=true` enables a source-reviewed Kroger case for exact Kroger merchant records. Four live primary-source reads verify case identity, court-linked documents, period and deadline. Changed PDF hashes require manual source/rule review. Insurance, geography, exclusions and proof stay unknown; packets are information drafts only. See `docs/evidence/p1-settlement-live.json`.

See `docs/SPONSORS.md`: Bright Data search succeeded but scraping is blocked by account activation. No deployment, video-generation sponsor or analytics database is claimed. Paid browser checks are opt-in: `P1_LIVE_E2E=1 WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test tests/p1-live.e2e.ts`. They may make two capped receipt calls on a fresh database. Start with `BRIGHTDATA_ENABLED=false OPENAI_ENABLED=false make dev WEB_PORT=3001` to avoid additional research/routing charges.

## Evidence and privacy

All five demo purchase records are synthetic. CPSC recall 26-792 is a recorded real government notice; snapshot URL/time/raw hash are in `demo/PROVENANCE.md`. Cards identify replay versus live. The five-row demo settlement is fictional and has no claim portal. The separately verified live Kroger case is always labeled distinctly, with personal eligibility unconfirmed. No payout balances or guarantees appear.

SQLite stores typed products, opportunities, evidence, assessments, packets, runs and ordered audit events. Raw receipts are processed in memory and not retained; FastAPI may spool multipart data to the OS temporary directory. CPSC response caches live under ignored `uploads/`, outside the webroot. Logs never contain raw receipts or credentials. Local approval does not attest disposal or supply missing names, signatures, photos or serial numbers. Changed evidence invalidates prior approval.

## Troubleshooting

- `uv` or `pnpm` missing: install prerequisites, then rerun `make setup`. Setup downloads a locked Python environment, Next dependencies and Chromium. uv cache/runtime default to task-specific `/tmp` paths; rerun setup if OS removes them.
- Port conflict: stop only your own server or select `WEB_PORT=3001`; backend still requires free port 8000. Do not terminate unrelated apps.
- Browser cannot reach API: use the same host/origin as `FRONTEND_ORIGIN`; Make defaults to `http://localhost:<WEB_PORT>`. API base can be overridden with `API_URL=http://localhost:8000` or `NEXT_PUBLIC_API_BASE_URL` in the process environment.
- Provider unavailable: inspect health and timeline. A failed live request falls back only when `DEMO_MODE=true`, with an explicit partial/replay label. With demo disabled it cannot produce fixture positives.
- Interrupted run: startup marks unfinished runs partial; trigger a new idempotency key. BackgroundTasks are process-local, not a durable job queue.
- Test warning: installed Starlette currently emits an upstream deprecation warning for its HTTPX-based TestClient. Tests still run and assert real API behavior; warning is recorded, not hidden.

Architecture, exact judge clicks, boundaries and remaining gaps: `docs/architecture.md`, `docs/DEMO.md`, `docs/known-limitations.md`.

Production builds use the bundled Webpack path (`next build --webpack`) because Turbopack could not bind its CSS helper port in this environment. Development keeps Next’s default bundler.
