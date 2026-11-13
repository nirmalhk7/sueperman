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

## Sentry handoff and OpenAI provider update — 2026-11-13

User approved two Sentry projects under `nirmalhk7/personal`: `sueperman-server` (FastAPI) and `sueperman-frontend` (Next.js). Installed/authenticated CLI using the handoff flow and checksum-verified installer. Credentials/DSNs remain in CLI-managed storage or ignored owner-only environment files, never source/evidence files.

User clarified System 1 is the decision role and selected OpenAI as provider. Added Responses API structured four-choice routing, configurable `OPENAI_DECISION_MODEL=gpt-6-luna`, `OPENAI_API_KEY` and `OPENAI_ENABLED`. No model tools; `store:false`; sanitized status/condition names only. Existing deterministic guards/fallback remain binding. Legacy vendor adapter is not selected by orchestration. OpenAI key is empty, so no live OpenAI success is claimed.

TDD evidence:

- OpenAI adapter RED: six expected missing-feature failures. GREEN: six transport/strict-choice/refusal/outage/override tests passed.
- OpenAI orchestration RED: decision mode `rules` vs expected `openai`. GREEN: configured request reached OpenAI transport and authoritative match/rejection/review counts stayed unchanged; guard override persisted.
- Python telemetry RED: real exceptions were discarded and trace scrubber missing. GREEN privacy tests passed. Actual SDK transport then caught literal private values copied through source context; source literals now redacted while retaining frame locations and code structure. Real SDK exception/trace/log envelope check passed.
- Browser telemetry RED: event/trace data leaked through identity stubs. GREEN sanitized outputs passed. Live checks revealed required source-map debug metadata and Replay correlation were being discarded; separate RED/GREEN regressions repaired both. Added JavaScript v11 streamed-span filtering after inspecting its installed contract.
- Temporary verification acceptance RED: backend 404 vs expected 500 and frontend verification button absent. GREEN: genuine running-app backend and browser errors delivered. Follow-up browser run verified replay delivery after correlation repair.
- Actual Sentry issues, traces, logs, replay and readable application frames verified via CLI. Initial browser frame lacked source context; uploaded temporary page's source-map pair and verified a new event mapped to original source. Proof: `docs/evidence/sentry-proof.json`, details/limits: `docs/sentry-setup.md`.
- Temporary trigger source and temporary browser checks removed. Fresh running-app checks confirmed both former URLs return 404.

Final checks after repairs/removal:

- `make test lint typecheck build`: exit 0; **54 backend tests**, **6 frontend unit tests**, Ruff/ESLint, MyPy (33 source files), TypeScript and Next.js production build passed. Output: `docs/evidence/monitoring-openai-checks.log`. Existing upstream TestClient deprecation warning remains visible.
- `make e2e smoke WEB_PORT=3001`: exit 0; **2 browser workflows** passed and offline demo retained all five expected outcomes and exactly one recall packet. Output: `docs/evidence/monitoring-browser-smoke.log`.
- No real claim submission or deployment occurred. Test issues remain open; no issue comments, reviewer requests or notifications were posted. Production environment/CI source-map upload remains a documented next step; local monitoring proof does not imply production verification.

Final review added three malformed OpenAI response-shape cases (top-level list, non-object output item, non-object message content). All three reproduced escaping AttributeError before repair; explicit shape validation now returns deterministic fallback. Nine decision adapter cases pass. Final full regression after this repair: 54 backend tests and 6 frontend unit tests, lint/type/build passed; current logs retain actual output. SDK configuration files additionally passed explicit ESLint.

## P1 continuation — 2026-11-13

User goal: complete P1, preserve P0; System One decision role uses OpenAI per SPEC override. No external submissions or P2.

Acceptance map (current work, not completion claims):
- P0 persistence/exact matching/negative/missing model/fixture labels/local approval/export: existing unit/integration tests, `make test`, `make e2e smoke WEB_PORT=3001`.
- Live official CPSC recall and provenance: live adapter, source-policy tests, actual request plus browser workflow.
- Bright Data MCP search_engine then scrape_as_markdown: transport tests, cold-start regression, actual MCP request, cited manufacturer evidence in detail/packet.
- Gemini image and PDF extraction: real SDK/schema validation tests, upload/API confirmation path, actual PNG/PDF requests (BLOCKED: GEMINI_API_KEY currently empty).
- Bounded decision routing: OpenAI transport/guardrail tests, selected/proposed action and sanitized evidence in UI, actual request (BLOCKED: OPENAI_API_KEY currently empty).
- Real open settlement: administrator/court-linked source validation, exact products/class period/deadline/unknown personal conditions/proof rules, deterministic tests, preparation-only packet, live sources/browser acceptance. Never infer declarations.
- Sentry: existing received-event/trace/log/replay proof retained; regression checks.
- DigitalOcean: conditional deployment only after local acceptance, BLOCKED missing credentials; document explicitly.
- Final regression/build/lint/types, live browser evidence, sponsor matrix and blocker audit required before completion.

Baseline `make test lint typecheck`: PASS 54 backend + 6 frontend, Ruff/ESLint/MyPy/TypeScript. Upstream Starlette TestClient deprecation warning remains.
Actual CPSC request: PASS one live NEWDERY record. Bright Data attempt: FAIL typed TimeoutError at existing ten-second total budget (including MCP cold startup). Repair underway test-first.

P1 first checkpoints:
- Bright Data RED: 2 tests failed (ten-second cold-start timeout, citation omitted model/remedy after navigation). GREEN: 10 Bright Data/optional-provider tests passed after 45-second bounded MCP session and relevant-line excerpts.
- UI decision evidence RED: browser missing Investigation decision heading. GREEN: 1 targeted browser test passed after rendering action/provider/hard-gate status/missing conditions/proposal/override.
- Gemini output-budget RED: missing maxOutputTokens. GREEN: 9 SDK/provider tests passed with 1024-token cap and SDK attempts=1.
- Live model check: exactly 2 Gemini generation attempts (one synthetic PNG, one PDF), both ClientError; no successful extraction claimed. Free model-catalog GET=200 confirms configured default model available. OpenAI: one live gpt-6-luna response selected request_user_info (mode=openai), sanitized proof docs/evidence/p1-model-live.json.
- Bright Data: real MCP initialized with exactly search_engine and scrape_as_markdown; search returned 3473 characters; scrape returned typed error: Customer is not active. No scraping success claimed. No further paid probes while fixing offline behavior.

P1 further checkpoints (observed, not inferred):
- Receipt confirmation RED: PNG/PDF integration expected 422 for unconfirmed review but route returned 404. GREEN: upload → explicit identifier confirmation → exact recall match passes for both types; editing after a checked opportunity returns 409.
- Duplicate extraction RED: identical upload invoked Gemini twice. GREEN: existing digest import now returns prior IDs before remote extraction; targeted three-test confirmation/import suite passes.
- Real settlement RED: absent provider/matcher/composer and zero persisted cases. GREEN: four-source official adapter, deterministic uncertainty/expiry/date/merchant gates, persisted evidence/assessment, preparation-only draft and local approval/export; 11 workflow/regression tests passed at checkpoint.
- Source review RED: unreviewed PDF revision did not fail; notice excerpt omitted deadline/proof. GREEN: reviewed document hashes fail closed; genuine notice passages include deadline, $8,000 documentation threshold and Unknown Claimant requirements. Eight source/workflow tests pass. Primary document records and hashes are in tests/fixtures/settlement/PROVENANCE.json.
- UI RED: no source label helper, missing review form and lingering Unverified scan after confirmation. GREEN: separate real/simulated labels, explicit review checkbox and confirmed state, selected/proposed decision and hard-gate evidence. Targeted browser regressions passed.
- OpenAI budget RED: configured maximum 1 still made 3 calls. GREEN: maximum 3 by default (configurable 0–10), deterministic labeled fallback beyond budget. Two OpenAI workflow tests pass; no paid OpenAI probes beyond the original single real call.
- Gemini live diagnosis: legacy response_schema serialized unsupported additional_properties (HTTP 400); configured 2.5 model returned 404 for this account; 3.5 requires at least a 10-second HTTP deadline. Free catalog/input-token checks succeeded. Full Pydantic wire schema still returned 400; tiny structural schema succeeded. Adapter now uses the accepted structural schema, with full strict Pydantic dates/lengths/extra-field checks retained locally. Current model preserves sampling defaults and uses minimal thinking. 1,024 output-token cap, SDK attempts=1. Diagnostic failures retained in p1-gemini-diagnostics.json; no billing total asserted.
- Actual PNG and PDF app uploads succeeded with model gemini-3.5-flash-lite, suggested ZHX-PB22, and unconfirmed identifiers. Persisted evidence: p1-gemini-api-live.json. First live image browser flow passed confirmation → live CPSC → local approval/export. PDF browser test initially selected an older image row; corrected stable product identity and response waits. Subsequent three-test live browser suite passed with cached receipt imports (no additional Gemini calls): image/recall, PDF review, live settlement draft/export.
- Real settlement discovery: administrator site, document index, long notice and administrator-hosted amended court order successfully retrieved through production adapter. Case 2:21-cv-00022; current documented deadline 2026-12-21; purchase window 2018-12-09–2026-08-23. No personal eligibility, signatures or payments asserted. Sources and exact observations in p1-settlement-live.json.
- Bright Data remains BLOCKED: search succeeded, scrape returned Customer is not active. User explicitly requested no further Bright Data calls and will resolve activation. Runtime verification disables Bright Data and OpenAI to avoid extra charges. DigitalOcean deployment remains BLOCKED by missing credential; no public deployment success claimed. No P2 work.
- Final first full check reached 73 backend + 7 frontend passes, lint clean, then MyPy caught string vs ThinkingLevel enum typing. Replaced string with the SDK enum (same serialized value); rerunning full checks before commit.
- Final review routing repair RED: inspect_more on an ambiguous official recall did not obtain manufacturer evidence. GREEN: selected action now records a typed INVESTIGATION_ROUTED event, request_user_info records NEEDS_INFO, inspect_more can invoke the bounded researcher for ambiguous candidates, and missing model still blocks packets. Thirteen routing/P0 workflow tests passed at checkpoint. Bright Data live access remains disabled per user.
- Final review identifier repair RED: confirming only a model silently retained an extracted brand; UI omitted reviewed brand in its payload. Added editable brand review; omitted brand stays unknown instead of becoming verified. Dates/eligibility remain gated. Brand/model/UPC confirmation uses no additional model call.
- Turbopack production build failed twice (including approved escalation): helper process/port binding denied. Read bundled Next CLI docs and changed build script to supported `next build --webpack`. Actual optimized build then passed with all four application routes. No deployment claimed. Build output: p1-build.log; failed runs remain in p1-checks.log.

Final verification for this P1 checkpoint — 2026-11-13:
- `make test lint typecheck build`: PASS, 75 backend tests + 7 frontend unit tests, Ruff/ESLint clean, MyPy (34 files)/TypeScript clean, optimized Next Webpack build passed. `docs/evidence/p1-final-checks.log`. The prior Turbopack failure remains recorded separately; no check was waived.
- `make e2e smoke WEB_PORT=3001`: initially exposed two browser-test issues. Missing-model assertion could resolve on dashboard text during navigation, and new decision test depended on data reset by another test. Strengthened detail URL/heading waits and made decision test seed/run its own fixture. Expected P0 facts unchanged. Final PASS: 4 offline browser flows; 3 paid/live tests deliberately skipped in ordinary suite, then explicitly invoked below. Smoke PASS: 5 purchases, 4 opportunities, 1 exact recall, 1 exclusion, 1 missing-model review, 1 simulated settlement, 1 recall packet. `p1-browser-smoke.log`.
- `P1_LIVE_E2E=1 WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test tests/p1-live.e2e.ts --output=../../output/playwright/p1-final`: PASS 3 flows (image/recall/local export, PDF review, real settlement sources/local export). Existing receipt imports reused; no additional model requests. Current CPSC/settlement reads remain actual live HTTP requests. Screenshots/videos under `output/playwright/p1-final/`; `p1-live-browser.log`.
- After browser-test repairs: `pnpm --dir apps/web lint` and `pnpm --dir apps/web typecheck`: PASS.
- Actual final source adapter read: PASS all four primary settlement documents, reviewed hashes and deadline verified; refreshed `p1-settlement-live.json`. P0 and simulated settlement remain separate.
- Candidate-repository scan found zero configured credential values; ignored `.env` and frontend `.env.local` remain mode 600. No secret value printed. Review of final source diff completed.
- P1 completion audit: P0 preserved; CPSC live, Gemini PNG/PDF live, OpenAI live decision, UI decision evidence, deterministic settlement checking/preparation, source provenance and local browser workflows proven. Bright Data scrape criterion UNMET (account inactive; user handling activation, calls stopped). Public DigitalOcean URL/health UNMET (credential unavailable; no deployment). Goal remains active/incomplete; no P2 or external claim submissions.
