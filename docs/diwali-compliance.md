# Sueperman V2 implementation and release record

Selected specification: [V2 counterexample review](https://chatgpt.com/space/page_5e3614ac8e1881919f5c373fb4ee1310), not V2.1 offline gates.

**Implemented locally: synthetic-only counterexample workflow, offline replay and configured live sponsor runtime path. Not yet a qualifying five-sponsor release.** No sponsor has live execution evidence from this work. The replay is a deterministic local control with three addressed role functions, not independently hosted/model-powered agents. It cannot establish the research hypothesis or sponsor qualification.

## What runs

From a synthetic recall opportunity, choose **Investigate with agent team**. Scout proposes the recorded supported notice; Skeptic checks false/unknown deterministic conditions; Builder consumes that reply to explain exclusion or choose one missing fact. The browser shows Finding, Challenge, Missing information, Decision, Evidence, and ordered request/reply events. Replay labels are explicit. Selecting live mode discloses sanitized sharing and invokes actual configured sponsor adapters only when all setup checks pass; missing configuration returns partial. See [runtime setup](diwali-runtime.md).

The one-question priority is model, serial prefix/batch, required purchase date, region, UPC, brand. Only conditions actually unknown in the supplied notice are asked; an exclusion suppresses questions. Answers require explicit confirmation, create a case-local revision, and never update V1 purchases. Exact matches support local draft review, approval and Markdown export on the case board. No submission or declaration is performed.

New APIs: `POST /api/collaborations`, `GET /api/collaborations/{id}`, `GET .../events`, `POST .../answers`, `POST .../approve-local`, `POST .../export`. One product per case is the bounded P0 implementation. Existing V1 endpoints and settlement behavior remain available.

Each revision binds sanitized case facts, evidence, rule version and local checklist hash. Approval binds the packet hash and revision. Changed original facts, rule/skill identifiers, retained evidence, fixture contents or the current V1 primary recall record invalidate the case on read/approval/export. Earlier revisions and source snapshots remain inspectable. Changes to observation metadata can conservatively require renewed review. Explicit synthetic demo reset deletes synthetic case history, as it already deletes V1 demo history.

## Persistence and reviewed additive migration

The existing `database()` initializer uses SQLAlchemy `create_all`; it creates five new tables: `collaborations`, `collaboration_revisions`, `collaboration_tasks`, `collaboration_evidence`, `collaboration_usage`. No existing column/table is altered or dropped. Foreign keys and uniqueness constraints bind tasks, revisions and evidence to cases. A disposable populated V1 database migration test compares every existing row, retains an approved historical packet and checks foreign keys. No migration was applied to a user purchase database.

Task intent is committed before role dispatch; the validated result is committed before board updates. Duplicate results cannot append another event. Wrong-case, stale, fabricated-reference and conflicting duplicate results are rejected. Startup marks incomplete work partial; no transparent resumption or exactly-once external execution is promised. The ledger is local SQLite authority, not BAND.

The local run has one shared configurable deadline of at most 90 seconds, three sequential requests, zero model calls and no retries. The ledger caps requests at six per revision. The API allows one active team case and defaults to 30 run starts/day, including answer revisions. The counter survives synthetic demo reset. Answers start a fresh bounded revision; this quota is not a billing guarantee. Live provider switches default off. Configured runs use BAND addressed delivery, Agent37 source execution, AdaL challenge and Lyzr construction; two model requests and one source command share the deadline. Missing setup, incomplete results or shutdown uncertainty leave a partial case. Vendor-internal call counts and cancellation require live verification.

## Sponsor boundaries and exact blockers

| Sponsor | Implemented/tested locally | Still required |
| --- | --- | --- |
| BAND | Pinned SDK 9.1.0 lifecycle, separate identities, addressed REST requests/replies, authenticated sender checks, deduplication, recipient receipts and cancellation tested with loopback transport | Account, four registered identities/keys and room; real handshake and correlated message references |
| Agent37 | Fixed-command exec adapter; exact Git revision check; supported CPSC worker; wired to BAND Scout; failure sanitization/no retry | Key, provisioned instance at `/app/sueperman` containing reviewed worker; actual read/exec receipt; verified network/process restrictions |
| AdaL | Official SDK pinned by commit; actual options/event interface, disabled tools and deny-all callback; isolated-workspace invocation and strict result validation | Authenticated native CLI bundle and exact service hosts; repeat denial checks with that bundle; real review session and Video Producer project/export |
| Finch | Reviewed manifest and package hash verification; bounded ZIP primary-document support without extraction; challenge consumes hash-pinned bytes; drift revokes export | Suitable real package download, license/content review and invocation record. Candidate public listings require login and are not proven suitable |
| Lyzr | Actual v3 HTTP profiles, stable per-case session, one POST/no redirects/retry, validated response feeds board through deterministic guards | Studio agent, workspace-generated endpoint/profile and key; real response and correlated visible board |

No live sponsor credentials or authenticated AdaL runtime are configured. Optional SDKs are installed and interface-tested. `scripts/diwali_preflight.py` reports setup gaps without network calls or secret output. Real live acceptance remains blocked; `P1_LIVE_E2E=1` is V1-only. See [exact runtime configuration and proof procedure](diwali-runtime.md).

Implementation references consulted: [BAND quickstart](https://docs.band.ai/quickstart), [Agent37 exec](https://www.agent37.com/docs/agents-api/exec.md), [AdaL permissions](https://docs.sylph.ai/integration/sdk/permissions/), [Lyzr agents](https://docs.lyzr.ai/enterprise/get-started/concepts/agents), [Finch delivery](https://www.finchtech.ai/en/story/use-skills). Documentation access is not execution proof.

## Requirement coverage

| ID | Local evidence / remaining release gap |
| --- | --- |
| R01 | Existing backend/frontend and browser regression suites; five-purchase replay remains intact. |
| R02 | Exact, near-match, suffix/punctuation, missing-model workflow and deterministic tests. |
| R03 | Local roles and real SDK-model loopback request/reply workflow tested; **live BAND handshake blocked**. |
| R04 | Agent37 HTTP double and pinned worker implemented; **live sandbox execution blocked**. |
| R05 | Actual SDK wire protocol and four denied tool requests tested through the Docker launcher; OS filesystem/network/environment isolation tested. **Native authenticated runtime and live review unproven**. |
| R06 | Package integrity and authored portable draft pass five vectors in two clean processes; reviewed public candidate unsuitable. **Finch delivery/invocation blocked**. |
| R07 | Builder schema/citation guard and replay UI tested; v3 adapter tested with HTTP doubles; **live execution blocked**. |
| R08 | Typed finding codes; unknown fields/freeform payment claims rejected; false/unknown conditions cannot become approved. |
| R09 | Explicit revision-bound answer, priority question and browser refresh; no V1 product mutation. |
| R10 | Product/rule/skill/evidence/packet drift and stale export integration tests, including a later live source snapshot invalidating an earlier case; retained history; browser export-error handling. V1 retains its existing evidence invalidation path. |
| R11 | Ledger uniqueness, duplicate/conflicting/stale/wrong-case results and request idempotency tested. External delivery/restart replay not proven. |
| R12 | Source outage, role exception, deadline and controller restart produce partial; no retry or secret error leakage. Live provider fault acceptance blocked. A timed-out BAND request cancels its local provider coroutine; remote cancellation still needs verification. |
| R13 | Allowlisted official URLs, minimal product fields, no private provider references in role events; synthetic-only boundary. Live payload trace inspection blocked. |
| R14 | No-key backend and browser replay; visible replay modes and `live_sponsor_proof=false`. |
| R15 | Synthetic product rejection, daily creation quota, one active case, deadline and task bounds; **live vendor-internal call counts/cancellation and deployed V2 smoke unproven**. |
| R16 | Populated disposable V1 migration preserves every old row and historical packet. |
| R17 | Browser exact/exclusion/missing-answer/refresh/local-export paths; real hosted role outcomes blocked. |
| R18 | Authorship/baseline preserved in manifest; Existing public repository/README anonymously readable; local V2 changes unpublished. **Roster, AdaL video and submission channel unverified**. |

## Authorship and media

See [evidence manifest](evidence/diwali/manifest.json). Checkout was clean on environment branch `work`, at `1dbd30f`, matching the specified baseline; no local `codex/sueperman` branch was present. Existing film assets were not edited. V2 work is uncommitted and has not been pushed. Participant event-authorship confirmation is recorded as user evidence, not an organizer waiver.

The selected spec's proposed 110-second storyboard remains the media target. The [demo production brief](diwali-demo.md) prepares the 110-second story. An AdaL-produced MP4, project receipt, `ffprobe` duration ≤120 seconds, audio/caption review and anonymous video access are still required. The existing GitHub repository/README was anonymously readable on 2026-11-15; these V2 changes remain local. Existing HyperFrames media is not a substitute. No video or sponsor usage claim is made.

No usability pilots were performed (0/5). The local replay cannot demonstrate a model Skeptic's incremental value over rule-only output. Independent local skill replay passes five vectors. Three live bounded runs, provider-disable fault proof and the agent-value comparison remain release work.

## Final unauthenticated continuation

The restricted AdaL launcher, hash-verified offline container route, bounded opt-in live acceptance runner and 110-second narrated/captioned rehearsal are implemented. Production container acceptance passes four browser tests. The rehearsal is prominently marked offline and not AdaL-produced; it is preparation footage, not qualifying live proof. See [verification](evidence/diwali/verification.md) and [Finch review](finch-review.md). All five real sponsor receipts, actual AdaL production and observational experiments remain external gates.
