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


## Deployment preparation and source-refresh safety — 2026-11-13

DigitalOcean operator credential was supplied and saved only in ignored root `.env` (mode 600). Account authentication succeeded. No app was created. The exact current `deploy/app-spec.json` received HTTP 200 from the non-mutating proposal endpoint: available name and $10/month base cost. Proposal evidence includes the exact spec SHA-256. Actual public deployment/health remains unverified.

Acceptance additions and observed red/green:
- Same-origin API configuration: a process-isolated frontend behavior test failed because an explicit empty public base URL fell back to localhost. Nullish fallback now preserves the empty string; unset and explicit remote URL cases also pass.
- Production packaging: real AMD64 container builds exposed missing useradd PATH, missing pnpm build policy, and unsupported daemon bind-mount access. Fixed PATH, copied existing workspace build policy before dependency installation, and used a normal COPY-based test gateway image. API/web run non-root; private environment files are excluded. No provider keys enter the test containers.
- Shared-demo disclosure: executable container acceptance failed on the prior LOCAL label. Production builds now display SHARED DEMO and tell visitors to use synthetic purchases because this demo has no account isolation.
- Stale settlement sources: integration test reproduced HTTP 200 export after a previously approved source document changed, instead of expected 409. Failed verification now invalidates real settlement evidence status and prior approval, blocks packet creation/export, and preserves historical evidence as unavailable. Restored verified sources require fresh approval. Simulated fixtures remain separate. UI test reproduced missing unavailable-source warning; warning and disabled approval/export now pass.

Final current-code verification:
- `make test lint typecheck build`: exit 0, 76 backend tests, 11 frontend tests, Ruff/ESLint, MyPy (34 files), TypeScript and optimized production build pass. Evidence: `p1-deployment-regression.log`. Existing upstream TestClient deprecation warning remains.
- `make container-test`: exit 0. Real Linux AMD64 API/web/gateway images, same-origin HTTP health, five exact fixture outcomes, negative and approval gates, local export, non-root users, env-file exclusion, Node/npm availability, plus one production-browser workflow passed. Evidence: `p1-container-check.log`, recordings under `output/playwright/container/`. Isolated containers/network/volume removed afterward. All providers disabled; no model calls.
- `make e2e smoke WEB_PORT=3001`: exit 0, five offline browser flows passed; three opt-in live tests skipped deliberately. Exact five-purchase fixture outcomes preserved. Evidence: `p1-deployment-browser.log`.
- `P1_LIVE_E2E=1 WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test tests/p1-live.e2e.ts --grep 'live settlement sources' --output=../../output/playwright/p1-deployment`: exit 0, one live settlement browser workflow passed after the safety repair. Genuine public primary-source reads; no Gemini/OpenAI/Bright Data calls. Evidence: `p1-deployment-live.log`.
- `git diff --check`: pass. Final source/deployment diff reviewed. Exact proposal hash verified. Candidate tracked/untracked nonignored files contain zero configured credential values. Root `.env` remains ignored and mode 600.

Remaining criteria: publish tested source branch with specific authorization, then create/verify public DigitalOcean app; Bright Data manufacturer scrape remains unproven and calls remain stopped per user. No P1 completion claim, P2 work, external claim submissions, GitHub posts or pushes.


## Approved public deployment — 2026-11-13

User explicitly approved pushing tested commits to `origin/codex/sueperman` and deploying the two-service $10/month base-cost App Platform app. `git push origin codex/sueperman` succeeded, 7ece40c..4aee3c3. No PR, comments, messages or claim submissions.

Actual deployment checks and repair:
- Empty app listing was HTTP 200 with only pagination; initial duplicate-check script incorrectly expected an apps array and stopped before creation. Correctly handled the observed empty response.
- Real app-create acceptance RED: GitHub source returned HTTP 400, `GitHub user not authenticated`. Unauthenticated GitHub repository metadata confirmed the existing repo is public. Changed only source configuration to DigitalOcean's documented public Git clone URL, same branch. Fresh non-mutating proposal HTTP 200 retained $10 base cost and exact spec hash. Actual create then succeeded; no duplicate app.
- App 044b649f-018f-4062-bd9a-195919becfb3; deployment ac96b96b-f2f5-49f9-a808-971f110322b4; both component commit hashes 4aee3c33dc3be937e0b4de04ac198488f620714b. Observed BUILDING, DEPLOYING, then ACTIVE through the same job. No restarts or duplicate deployments.
- Public URL: https://sueperman-6t4xk.ondigitalocean.app. Genuine HTTPS GET `/api/health` and `/` HTTP 200; database ok and shared synthetic-purchase warning visible. Gemini/OpenAI/Bright Data disabled and unconfigured publicly; no provider keys sent to cloud.
- `WEB_URL=https://sueperman-6t4xk.ondigitalocean.app pnpm --dir apps/web exec playwright test tests/workflow.e2e.ts --grep 'five purchases produce evidence-backed recall' --output=../../output/playwright/digitalocean`: exit 0, one complete public production-browser fixture workflow passed, 15.6 seconds. Exact match, near-match rejection, missing-model review, simulated case, approval-before-download remain intact.
- Deployed live API acceptance imported two visibly synthetic CSV records. First descriptive recall test name omitted the product family and was correctly rejected by hard gates. Corrected test input to say power bank; no code/rules relaxed. Run d3230caa-dc5c-4842-b8e0-bad561d89afa completed with live CPSC exact recall and four-source verified settlement; personal eligibility uncertain, no simulation, no paid provider calls. Unapproved export blocked for both packets.
- Temporary Chromium acceptance script checked both existing live results through public UI. First locator incorrectly demanded exact source-only text despite an adjoining timestamp; updated locator to match actual full source paragraph, consistent with existing local live test. Actual two workflows then passed: visible live evidence/decision, settlement preparation-only uncertainty, local review checkbox, approval and Markdown download. Temporary script removed; screenshots, drafts/video and actual output retained under output/playwright/digitalocean-live and p1-digitalocean-live-browser.log; failed first locator log retained separately. No application behavior changed for this test repair.
- Current evidence: p1-digitalocean-deployment.json, p1-digitalocean-public.json, p1-digitalocean-proposal.json, p1-digitalocean-browser.log, p1-digitalocean-live.json, p1-digitalocean-live-browser.log.

Current P1 audit: public deployment criterion now met. CPSC, Gemini PNG/PDF, OpenAI bounded decision role, deterministic source-backed settlement preparation, local/public browser flows and P0 regression evidence exist. Bright Data live search succeeded but manufacturer scrape remains UNMET: last actual error Customer is not active, further calls stopped per user. Production Sentry delivery remains unverified and is not inferred from local monitoring proof. No P1 completion claim or P2 work.


## Bright Data activation and final P1 verification — 2026-11-13

User requested a fresh Bright Data check after activating the account. No Gemini/OpenAI calls were made during this work. The isolated paid-research API was stopped after verification; public paid features remain disabled.

Observed live results and repairs:
- First production-adapter check initialized the official MCP server and exposed only search_engine/scrape_as_markdown, but the 45-second deadline canceled search. No new inactive-account error was returned. Evidence: p1-brightdata-recheck.json. Historical inactive result retained in p1-brightdata-before-activation.json.
- One longer-deadline diagnostic succeeded: search_engine 47.476521 seconds / 2923 characters, scrape_as_markdown 3.428267 seconds / 8694 characters. This confirmed activation and actual tool execution; no fixture substituted. Diagnostic excerpt reflects the then-broken parser and is historical, not the usable citation proof.
- TDD RED: scaled real asyncio deadlines reproduced cancellation of a 52-second search; JSON-wrapped scraped content reproduced missing model/remedy in the saved excerpt. GREEN: bounded research timeout increased to 75 seconds, still below existing 90-second overall run cap; JSON content decoded before selecting relevant lines.
- First isolated app run invoked both tools successfully but revealed the current official MCP's additional nonce-delimited SECURITY NOTICE wrapper. Inspected installed official MCP source; matching nonce markers enclose inert page data. Parameterized wrapper regression RED, then GREEN after decoding that envelope before JSON. No page instructions gain tool privileges or eligibility authority. Legacy plain text remains supported.
- Final isolated API run e7bd4e7c-e44b-4b9c-b4e1-fa7c9290dd41 completed with live CPSC and Bright Data, exact recall hard gates intact, and readable NEWDERY model/refund evidence persisted. The existing packet uses CPSC as authoritative Markdown source and the manufacturer URL as contact_or_portal_url. An initial acceptance assertion incorrectly expected the supplemental URL in Markdown; corrected it to verify the actual documented handoff field plus authoritative CPSC citation, without changing the packet or any product requirement. Evidence: p1-brightdata-app-live.json.
- Actual Chromium workflow displayed the linked NEWDERY manufacturer excerpt with ZHX-PB22/refund text, live CPSC label and explicit local approval/export. Browser requests were forwarded to the isolated port-8002 API; no responses stubbed. No new provider requests during browser verification. Screenshots/video: output/playwright/brightdata-live; output: p1-brightdata-browser.log. Isolated API process stopped afterward.

Final current-code checks:
- `make test lint typecheck`: exit 0, 79 backend + 11 frontend tests; Ruff/ESLint/MyPy (34 files)/TypeScript pass. p1-brightdata-regression.log. Existing upstream TestClient deprecation warning retained.
- Targeted Bright Data/optional-provider suite: 13 passed; p1-brightdata-repair-green.log. Expected RED output retained separately for deadline, JSON and nonce-wrapper bugs.
- `make build`: exit 0, optimized Next Webpack build; p1-brightdata-build.log.
- `make e2e smoke WEB_PORT=3001`: exit 0, five offline browser flows passed, three opt-in live model/source tests skipped deliberately; exact fixture counts unchanged. p1-brightdata-p0-browser.log.
- Bright Data live app/browser workflow above passed after the final parser repair. Prior genuine Gemini PNG/PDF, OpenAI decision, public CPSC/settlement browser and Sentry monitoring evidence remain applicable; those implementations were not changed and paid model requests were not repeated.

Completion audit against the P1 objective:
- P0 preservation: current full regression and browser/smoke results above; negative/missing-model/simulation/local-review/export gates remain intact.
- CPSC: live official API source, exact matching and source provenance proven locally and publicly (p1-digitalocean-live.json; live-cpsc.json).
- Bright Data: both official MCP tools succeed; production adapter, persisted manufacturer citation and live UI/local packet workflow proven (p1-brightdata-status.json; p1-brightdata-app-live.json).
- Gemini: genuine image and PDF extraction, strict local structured validation and explicit identifier confirmation proven (p1-gemini-api-live.json; p1-live-browser.log); no new receipt calls needed.
- System 1 role, user-selected OpenAI provider: real gpt-6-luna request succeeded (p1-model-live.json); four-choice schema, sanitized state, budget, routing and hard-gate override covered by current tests; decision/action evidence appears in tested UI. No System One vendor claim.
- Settlement: real administrator/court-linked sources, reviewed hashes, open deadline, deterministic date/merchant/expiry gates and missing-condition uncertainty; only preparation/local export, no declarations or payout promises. Genuine local/public browser evidence: p1-settlement-live.json, p1-digitalocean-live.json.
- UI provenance and source links: fixture/live/simulated labels, manufacturer citation and selected-action/guard evidence verified by current browser tests plus live recordings.
- Deployment: previously observed ACTIVE two-service app with public health/home HTTP 200 and public fixture/live-source browser flows; p1-digitalocean-deployment.json and related evidence. Paid model/research features remain off publicly to protect credits. This repair has not redeployed the public image.
- Sentry: existing real local errors/traces/logs/masked replay/readable frames (sentry-proof.json); production monitoring delivery is explicitly unverified, not a P1 live-integration claim.
- Docs and actual commands/results updated; no secrets in source, external claim submissions, fabricated purchases presented as real, or P2 work. Remaining documented boundaries concern coverage, shared ephemeral demo storage, public paid flags and production monitoring; no missing credential/account blocker remains for the required P1 integrations.


## Receipt camera and user-selected OpenAI OCR — 2026-11-13

User requested photographing a receipt and reading it, then explicitly chose OpenAI credits. Scope: mobile rear-camera preference plus desktop photo fallback; existing upload/normalized-product/review flow; separate OpenAI photo extraction and bounded public spend. Existing Gemini image/PDF extraction, CSV, hard eligibility gates and identifier confirmation remain supported. Separate uncommitted logo/video edits are excluded from this change.

Acceptance mapping and observed red/green:
- Camera request/JPEG upload/read-in-progress/review-only results and failed-upload retry: new mobile Playwright tests initially failed because no camera input existed. Added capture=environment with JPEG/PNG accept, reading feedback, disabled controls while reading and input reset. First green attempt caught overly broad status/alert test locators (existing Processing status and Next route announcer); scoped to intended messages. Final two tests pass without model calls.
- OpenAI image extraction/shared strict receipt validation: initial integration tests returned 503 without any OpenAI request. New adapter uses vision-capable gpt-6-luna Responses API with strict structured output, store:false, no model tools, 1024 output-token cap and no retry. Merchant/date/item extraction, unknown identifiers, refusal/incomplete/invalid date/empty item rejection and duplicate reuse pass with actual transport boundaries doubled offline.
- Image preparation: missing module RED; real JPEG decode/orientation/downsize/no EXIF/corruption checks GREEN. Added locked Pillow dependency. No raw image or camera metadata is added to stored product facts.
- Shared daily budget: restart persistence and concurrent reservation tests RED before implementation; GREEN with atomic SQLite counter. Default 10 attempted requests per UTC day; duplicates checked before budget reservation; failed attempts remain counted. This is a request limit, not a provider monetary budget, and public ephemeral SQLite can reset on redeploy.
- Installing Pillow exposed a pre-existing Gemini mixed-list type inference issue in MyPy. Typed the equivalent SDK user Content/Parts explicitly. Existing Gemini transport/receipt tests remain green; no extra paid Gemini request.
- One genuine OpenAI upload of clearly synthetic JPEG returned merchant Demo Store, Portable Power Bank, date 2024-06-12; identifiers stayed unconfirmed. Evidence: receipt-camera-openai-live.json. Real mobile-browser input/upload/review used that cached photo (zero additional model calls): receipt-camera-live-browser.log and output/playwright/receipt-camera-live/mobile-reading.png.

Local checkpoint:
- `make test lint typecheck build`: exit 0; 88 backend tests, 11 frontend unit tests, Ruff/ESLint, MyPy (35 files), TypeScript and optimized Next Webpack build. receipt-camera-regression.log. Existing upstream TestClient deprecation warning remains.
- `make e2e smoke WEB_PORT=3001`: exit 0; seven offline browser flows, three opt-in tests skipped; exact P0 fixture counts unchanged. receipt-camera-browser-smoke.log.
- OpenAI-specific targeted backend suite: nine passed. Two mobile camera browser tests passed. Red/green logs retained.
- Public receipt-photo deployment and actual public upload verification pending at this checkpoint. Runtime secret will be sent only to the API service, never source/frontend/build. No claims submitted; no additional research/routing model calls.
