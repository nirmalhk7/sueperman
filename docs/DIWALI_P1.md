# Requested V2 P1 extension

The owner explicitly requested “move to P1. Satisfy all parts of P1.” This means the original V2 specification's three P1 items: additional tested recall normalizers, scheduled source-change monitoring, and obligation completion aids. It does not mean the separate, mostly implemented V1 P1 sponsor list. Moving scope does not complete or waive outstanding V2 P0 gates. Original baselines, fixtures and acceptance oracles remain unchanged.

## Implementation and acceptance map

| Requirement | Files/components | Executable acceptance |
| --- | --- | --- |
| Additional reviewed notices | `app/p1/normalizers.py`, pinned `normalizers.json`; opt-in CPSC source dispatch; real government capture fixtures | `tests/p1/test_normalizers.py`: exact/near/punctuation/missing/brand, changed full-record pin, conflicting duplicate, optional receipt; `test_api_normalizers.py`: upload/run/evidence/approval/export for both notices |
| Persistent, opt-in daily source monitoring | Separate additive P1 tables, monitor coordinator, FastAPI lifespan scheduler, read-only CPSC checker, capability/control/history API | `test_monitoring.py`: unchanged/changed/unavailable/recovered, two snapshots, export revocation, restart, bounded concurrency, no transaction across await, five-watch limit, active-run deferral; `test_monitor_api.py`: default off, operator permission, explicit user opt-in, closed input, idempotency, scheduler and registered public query |
| Local obligation completion aids | `app/p1/obligations.py`, P1 API, claim-screen checklist; readiness is self-reported; export requires renewed local approval | `test_obligations.py`: persistent state, explicit confirmation, stale-binding and unknown/extra-field rejection, approval invalidation, source/product/policy drift, no changes to eligibility or missing proof; `p1.e2e.ts`: reload and Markdown export |
| Preserve existing V1/V2 behavior | Existing APIs and five golden purchases; default-off feature flags; no new infrastructure or paid calls | Full `make test`, lint, typecheck, build, smoke, offline browser suites; frozen oracle and protected-path audit; distinguish existing BAND SDK lock extension from P1 (P1 adds no dependencies) |
| User-visible monitoring and source history | Opportunity controls, immutable snapshots and current review status; prior evidence is explicitly labeled; real recalls never inherit a simulation model fallback | `p1.e2e.ts`: opt-in/disable, unchanged/changed/unavailable source, old-export rejection, checklist persistence, empty/error states; `test_monitor_api.py`: operator capability |

## Source decisions

Reviewed CPSC notices: Flaunt `26-610`, model `E33A`; iStore `25-390`, model `IST-09991/W05`. Public API rows and official notices were read on November 15, 2026. Source metadata/hashes are in `docs/evidence/diwali/p1/sources.json`. Full-record pins fail closed on any upstream change. Only exact published models are supported; no model aliases are inferred. Flaunt's official “Battery Charger” family wording is an explicit source-reviewed alternative to “power bank”; the condition panel shows both. Normalizer rule version is `p1-2`. iStore's purchase receipt is explicitly optional and is not added as required proof.

VC Group `25-190` was inspected but not selected: its purchase-order restrictions require additional structured conditions. No unsupported record gains a positive normalizer. Existing NEWDERY fixtures and matching behavior remain intact. CPSC conflicting records for one recall now fail closed rather than hiding a changed restriction behind deduplication.

## Operational defaults

`P1_ENABLED=false` and `P1_MONITOR_ENABLED=false`. Additional normalizers require P1 plus live CPSC mode. Scheduled public reads require both flags, `CPSC_LIVE_ENABLED=true`, a running scheduler, and an explicit per-opportunity watch. Checks use registered public brand queries; no receipt bytes, merchant/order details or arbitrary supplied URLs enter a request. Fixed 24-hour schedule, five active watches, at most five sequential checks per tick, 60-second polling, 10-second remote-task cap, no immediate retry. Existing CPSC GET retry limit remains one. Watches defer while an investigation run is active.

Intent/next-due time persists before network I/O. Results commit in short transactions; no session crosses an await. Source changes/unavailability revoke local export. Recovery does not restore approval. Interrupted in-flight watches are disabled at restart pending explicit user action. Historical source snapshots remain in the check ledger while their parent opportunity exists; explicit demo reset may remove demo-owned rows through foreign-key cascades. This remains one FastAPI worker and SQLite, not a durable distributed scheduler or public multi-user service.

## Current checkpoint

All three additions are implemented with RED/GREEN records. Targeted P1 backend tests and four real-browser scenarios cover additional notices, readiness/reapproval/export, scheduled source changes/outages, and empty/error states. Controlled external responses in tests are not live provider proof. Separate `live-source-monitor.json` records actual public CPSC reads and actual scheduler consumption for both notices, using synthetic records in a disposable database. No paid call or submission occurred; both watches were disabled and the disposable server stopped.

Final verification results are generated in `docs/evidence/diwali/p1/regression-report.json` and the final acceptance report. No push, publication or deployment was performed. P1 completion does not close P0's BAND application wiring, Lyzr reviewer, required Finch package, Agent37 funding/integration, AdaL deferral or release assets.

The frozen baseline was not regenerated. `baseline-audit.json` distinguishes the authorized additive `.env.example` P1 flags and README instructions (all prior bytes retained), plus the pre-existing BAND SDK lock extension (no P1 dependency change). The original P0 baseline gate still reports those differences; this is not presented as a passing P0 gate. Earlier G3 regression log paths contain later regression runs; original structured handoff counts remain historical, and final P1 logs have their own directory.
