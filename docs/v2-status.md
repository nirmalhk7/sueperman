# V2 verified status — November 14, 2026 (America/Los_Angeles)

Historical checkpoint. Current sponsor status and remaining requirements: [DIWALI_SPONSOR_STATUS.md](DIWALI_SPONSOR_STATUS.md).

**P0 incomplete.** A deterministic offline vertical slice is implemented. W0 feasibility was checked, but five sponsor handshakes are blocked. W1 is implemented; W2 has strict ingress/role and package-pin boundaries only, with no vendor adapters. W3/W4 work offline. W5 has no live proof or deployment. W6 has no AdaL assets. This provisional offline progress does not establish the sponsor architecture.

## Account setup update

BAND Controller, Scout, Skeptic and Builder identities plus their room were created in the signed-in dashboard. Public listing, personal-registry access and webhook wakeup are off. The room contains those four identities and the account owner. Credentials and opaque routing references remain only in ignored `.env`.

Lyzr Builder was created with the application-derived structured-output schema (adapted to Studio’s supported JSON Schema subset), no tools/knowledge sources and cross-session memory off. Instructions were verified in saved Agent JSON after correcting the rich-text editor input. Standard API key and generated endpoint/request fields were saved locally. Creating that key disabled the legacy key, with separate explicit user approval. The live generated endpoint is `/v3/inference/chat/`; no Lyzr inference execution has been claimed.

Agent37 key is configured; the dashboard still shows $0.00 and no compute instance. After user sign-in, Finch Strategy Red Team v1 (Base 8453, skill 311, MIT) was downloaded through the browser. Published SKILL.md fingerprint matches; five text files were reviewed and attribution retained. Real-file pin and tamper checks pass. It is a candidate method only: recall suitability and model invocation remain unverified. AdaL is deferred at the user’s request. Account provisioning does not close live execution requirements, and the application live switch remains off.

## Implemented behavior

Additive case/task/result/event/snapshot/revision/draft tables preserve V1 data. Case results are schema-checked, cited, deduplicated and revision-bound; task requests are capped at six. Three local roles pass a typed challenge to Builder, which validates it against deterministic hard conditions. Existing matching remains the authority. Changed/unsupported source restrictions remain review-only. Every role/source is marked replay. Sources are allowlisted public CPSC records; arbitrary tool calls, unknown findings and fabricated citations are rejected.

The new opt-in board shows Finding, Challenge, Missing information, Decision and Evidence. Missing model asks one explicitly confirmed question and starts a fresh case revision without mutating V1 product facts. Near-match/suffix/punctuation exclusions cannot prepare a packet. Exact cases can review/approve/export a separate local team draft. Product, evidence, rule and skill changes revoke approval before export, while snapshots and revisions remain inspectable. Restart, malformed result, timeout and unavailable live team produce explicit partial status. Missing/invalid recorded evidence also creates a persisted partial case. Losing the recorded source after approval revokes export and keeps its prior snapshot. No automatic paid retry occurs because no sponsor call is implemented.

Public team admission defaults to synthetic demo products. One product per case and one active team run bound this P0 slice. V1 APIs remain unchanged; demo reset retains products referenced by case history. No account-isolation or durable-worker claim is made.

## Requirement accounting

“Offline verified” below does not close a requirement that also needs live/deployed evidence.

| ID | Actual status | Evidence / remaining criterion |
| --- | --- | --- |
| R01 | Regression verified locally | Existing tests, smoke, browser suite and build; paid V1 browser checks intentionally skipped. V1 CSV/OCR confirmation, recall, settlement, local review/export remain covered. |
| R02 | Offline verified | Exact ZHX-PB22, ZHX-PB23, suffix and punctuation variants, absent model; guard and API/browser tests. |
| R03 | Partial | Three addressed local tasks, cited challenge consumed by Builder, changed board verified. Four private BAND identities and case room now provisioned; actual SDK delegation/reply remains unimplemented. |
| R04 | Blocked | Agent37 key saved; $0.00 compute balance. No instance/pinned worker/real source-read receipt or adapter. |
| R05 | Blocked | Deferred by user; no runtime adapter, actual permission-denial test, OS restriction or live review trace. |
| R06 | Partial / live blocked | Reviewed manifest/hash tamper gate tested. Actual candidate package identity/license/delivery/content review and pin/tamper checks now recorded for Strategy Red Team v1, skill 311. Recall-specific suitability and actual model invocation remain pending; fixture tests alone are not sponsor execution proof. |
| R07 | Partial / live blocked | Board construction uses constrained local findings. Studio Builder, standard key and generated API configuration now provisioned; adapter, live validated response and visible application integration remain pending. |
| R08 | Offline verified | Fabricated citations/claims/commands/fields rejected; false/unknown gates cannot be changed by a purported passing challenge; unknown notice/restriction cannot verify. Vendor-boundary adversarial checks remain. |
| R09 | Offline verified for supported notice | Empty model asks one question; explicit answer, stale-answer rejection, case-only revision; priority unit check skips restrictions absent from supported notice. Additional notice-specific question paths are not claimed. |
| R10 | Offline verified | Separate tests for product/evidence/rule/skill changes blocking export, retained snapshots/revisions, current-run browser guard; draft hash bound to approval. |
| R11 | Offline verified | Unique run/task/event/revision/draft constraints, duplicate result/trigger/answer checks and stale/wrong-case validation. BAND redelivery still needs actual integration. |
| R12 | Offline verified / live pending | Injected outage/malformed result/real asyncio deadline, restart and late-result checks; no fake completion. Sponsor fault tests pending adapters. |
| R13 | Offline verified / live pending | Minimal fact projection, strict schemas, source allowlist, sanitized events/export; no receipt/order/merchant in team messages/export. Actual vendor payload inspection pending. |
| R14 | Verified offline | No-key tests and browser replay; every role/source labeled; empty live-proof list. |
| R15 | Partial | Synthetic-only default, one admitted run, one product/case, six-task cap, 90-second maximum and paid kill switch checked locally. Per-provider controls, six-model-call accounting, external concurrency/source bounds and deployed verification pending live adapters. |
| R16 | Verified locally | Disposable populated V1 database migration twice preserves purchases/products/opportunities/historical packet rows exactly; unique ledger keys tested. |
| R17 | Offline verified / live pending | Browser exact-after-answer, exclusion, unknown, reload, three cited role results and local export; newer run blocks previously open approved draft. Real provider outcomes pending. |
| R18 | Incomplete | Existing repository observed anonymously public; local V2 remains unpublished. Actual local git history recorded, but participant attestation/event eligibility remain unconfirmed; no AdaL project/video, final duration or final video-access check. |

No usability pilots or agent-value comparison was performed. No tested set is presented as proof of general recall coverage, legal eligibility, improved consumer outcomes or money recovery.

## Verification

Baseline before edits: `make test` — 89 backend + 11 frontend tests passed.

Final implementation:

| Command | Observed result |
| --- | --- |
| `make test` | 132 backend + 11 frontend passed; one existing Starlette TestClient deprecation warning |
| `make lint` | Ruff and ESLint passed |
| `make typecheck` | mypy (42 source files) and TypeScript passed |
| `WEB_URL=http://localhost:3012 make e2e` | 9 passed, 3 opt-in paid V1 tests skipped; includes 2 V2 browser flows |
| `WEB_URL=http://localhost:3012 make smoke` | Passed; offline V1 counts and same local API/frontend verified |
| `SENTRY_AUTH_TOKEN='' make build` | Production Webpack build passed, including `/collaborations/[id]`; source-map upload disabled |
| `make container-test` | Passed for final backend code: isolated production containers, same-origin V1 workflow/browser export, non-root processes and environment-file exclusion; not a deployed live V2 check |
| `git diff --check` | Passed |

Browser/smoke servers used disposable `/tmp/sueperman-v2-browser.db`, API port 8000, web port 3012, paid provider flags off. Existing port-3000 server was left alone. Test servers were stopped after verification. Build restored Next's generated production type paths without a tracked change. Existing film/slides edits were not changed.

TDD logs retain expected missing-feature RED and GREEN results for contracts, ledger, workflow/guards, revision/reset regression, skill tamper gate, adversarial challenge checks, task/late-result bounds and browser entry. Logs are copied under `docs/evidence/diwali/`; browser traces/videos stay under ignored `apps/web/test-results/`. These are test evidence, not sponsor proof.

For exact outstanding actions, follow [live runbook](diwali-live-runbook.md) in W0–W6 order. Five live proof receipts, real runtime restrictions, deployed gates and AdaL submission assets are mandatory before release.
