# Implementation log

2026-11-13. Conservative cutoff: 15:00 America/Los_Angeles; feature freeze 14:20. Official onsite deadline unconfirmed.

## Acceptance coverage

- P0 parser and typed products: `tests/unit/test_core.py`: Unicode, quoted CSV, duplicates, missing name, size cap.
- Exact recall, near-match rejection, unknown identifiers, conditional restrictions, unknown remedy, source authority: core tests.
- Five literal rows, official recorded CPSC source, replay labeling: core fixture test + browser test.
- Settlement class period/deadline, never real: core settlement test + browser simulation screen.
- SQLite state, idempotent imports/runs, durable ordered audit, API errors, health: workflow integration tests.
- Sourced packet, no attestations, local approval, gated Markdown export: workflow tests + browser download assertions.
- Upload/dashboard/run/detail/packet screens, required copy and mode badges: Playwright workflow.
- Root setup/dev/seed/demo/test/lint/typecheck/smoke commands: execute against running apps; production build additionally required.
- Provider timeout, malformed response, source validation, fallback and advisory-only routing: P1 adapter tests after offline gate.
- P1 live invocation evidence: CPSC network smoke; sponsor calls conditional on credentials.
- Required docs and sponsor matrix: manual diff review. External submissions and publication unauthorized/out of scope.

## Checkpoints

- PASS Phase 0: empty repository; no user code to preserve; Python 3.12.13 installed via uv; Node v24.1.0, pnpm 11.25.0. Required sponsor environment variables absent (presence only inspected).
- PASS 17:48Z: official CPSC notice downloaded to demo/cpsc-26-792.html; normalized current recall facts with raw hash.
- RED core: `services/api/.venv/bin/pytest services/api/tests/unit/test_core.py -q`: 15 expected missing-feature failures.
- GREEN core: same command: 15 passed.
- RED API: `services/api/.venv/bin/pytest services/api/tests/integration -q --tb=short`: 3 assertion failures, expected routes returned 404 against empty FastAPI app.
- GREEN API: `services/api/.venv/bin/pytest services/api/tests -q --tb=short`: 18 passed; upstream TestClient deprecation warning and asyncio scope warning observed.
- DOING browser flow: acceptance tests written before UI. Port 3000 belongs to unrelated career-ops Next server; preserving it, verifying Sueperman on 3001 with configured CORS. Default remains 3000 for clean clone.
- TODO P0 full root checks and browser artifacts.
- TODO P1 integrations in specified order; credentials absent must remain explicitly unproven.

## Final repair and integration checkpoints

- PASS CPSC: observed real REST response before normalizer implementation; production fixture recorded under tests/fixtures. RED 3 adapter failures; GREEN 3 passed. Live flag/fallback integration RED 2 failures (`partial` vs `completed`, replay mode vs fallback mode); repaired and passed.
- PASS optional provider boundaries: RED 6 missing-contract failures; GREEN 6 passed. Added actual Google SDK transport-shape characterization and redirect checks; no paid service invoked. Public System One catalog returned HTTP 200 and contains `decisions` with Choice capability; authenticated POST unproven.
- PASS stale packet regression: observed approval HTTP 200 where changed official evidence required 409. Packet invalidation, assessment/evidence refresh and approve/export hard gates repaired it.
- PASS Gemini upload: RED HTTP 422 vs required 200 with configured SDK transport; GREEN upload persists unconfirmed scan suggestions and cannot produce an exact-match positive from the model alone.
- PASS telemetry: RED missing sanitizer; GREEN raw receipts, credentials, requests, exception text and user fields are discarded. No Sentry DSN/event proof.
- PASS origin/card regressions: RED cross-origin reset returned 200 and list lacked purchase model; GREEN 403 and explicit comparison data.
- PASS browser import/demo regression: RED six rows vs five; GREEN selects only returned seed IDs and preserves imported history.
- PASS missing-brand candidate: RED zero records vs one candidate; GREEN product-family candidate retains needs-review status.
- PASS unknown source identity: RED rejected vs needs_review; GREEN fail-closed review.
- PASS candidate limits: RED duplicate count 2 vs 1 and overflow raised ProviderUnavailable; GREEN source deduplication and explicit ten-record truncation.

## Final observed verification (2026-11-13, America/Los_Angeles)

- `make setup`: exit 0; uv/Python dependencies, locked pnpm dependencies and Chromium available.
- `CPSC_LIVE_ENABLED=true make dev WEB_PORT=3001`: both servers started, API 8000 / web 3001. Unrelated port-3000 app preserved. Stopping API also stopped companion web process; restarted final source.
- `make test lint typecheck build`: exit 0; **41 pytest tests**, **1 frontend unit test**; Ruff/ESLint, MyPy (32 Python source files), TypeScript and production Next build passed. Actual output: `docs/evidence/final-checks.log`. One upstream Starlette TestClient deprecation warning remains visible.
- `make e2e WEB_PORT=3001`: exit 0; **2 browser tests**, including all five demo outcomes, official evidence, gated local approval/download and CSV/demo selection. Actual output: `docs/evidence/browser-checks.log`. Screenshots and browser recording copied to `output/playwright/`.
- `make smoke WEB_PORT=3001` then `make demo WEB_PORT=3001`: exit 0 twice. Both produced 5 scanned / 4 opportunities / 1 exact recall / 1 rejected / 1 review / 1 simulated settlement / 1 packet. Output: `docs/evidence/offline-smoke.log`.
- `PYTHONPATH=services/api services/api/.venv/bin/python scripts/live_cpsc_check.py`: exit 0, production adapter made real public lookup; exact ZHX-PB22 verified, ZHX-PB23 rejected; URL and observation timestamp in `docs/evidence/live-cpsc.json`.
- Actual local HTTP live run: completed, recall provider `cpsc`, three recall statuses correct and all mode=live. Envelope and URLs: `docs/evidence/live-run.json`.
- React review: native accessible controls, client-only effects, cancellation for run polling, independent polling requests batched, no external UI framework or browser-held provider credentials.
- BLOCKED optional remote proof: Bright Data/Gemini/System One keys, Sentry DSN and DigitalOcean credentials absent; doctl unavailable. No login troubleshooting or paid calls attempted. Optional integrations honestly marked PARTIAL/NOT IMPLEMENTED. No real open settlement claimed. All P2 deferred.
- PASS manual acceptance review: exact locked CSV rows, government raw snapshot/hash, simulation labels, evidence comparison, safety instructions, local approval/export, no submission endpoint, docs and required root commands present. Review distinguishes implemented P0 from optional remote proof gaps in known-limitations.md.
- DOING clean-clone acceptance and local checkpoint. No external publication authorized or performed.
- PASS clean clone: local source checkpoint `a0751b4` cloned to `/tmp/sueperman-clean-01a1d604`; optional keys explicitly empty and flags disabled. `make setup test lint typecheck build` exit 0; 41 backend + 1 frontend unit test, lint/type/build green. `make dev WEB_PORT=3001` booted both clean-clone apps. `make smoke demo e2e WEB_PORT=3001` exit 0; offline facts repeated twice and both browser tests passed. Actual output: `docs/evidence/clean-clone.log`.
- PASS staged review: code/docs whitespace check excludes byte-preserved official HTML and raw console logs; raw HTML has original whitespace. Independently hashed staged HTML bytes and matched `demo/PROVENANCE.md`. Reviewed source policy, workflow, claim gates, route contracts and full staged file list; no real credential values or external filing path introduced.
- PASS delivery: source checkpoint `a0751b4` on local branch `codex/sueperman`; subsequent checkpoint records clean-clone evidence only. P0 accepted. Paid integrations/cloud remain explicitly unproven; no P2 implementation or external publication.
