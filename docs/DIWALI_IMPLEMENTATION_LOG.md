# V2.1 implementation

Baseline: `harness/diwali/baseline.json`. Frozen acceptance and expected outcomes are unchanged. Existing V1 SPEC and previous offline collaboration implementation remain intact. Scope is G0–G3; provider gates and paid calls are disabled.

## Legacy change manifest

The baseline names run dispatch/schema, settings, app setup, existing run view/client, and Makefile as integration boundaries. Additional required legacy edit: `services/api/app/api/claims.py` calls the Diwali stale-input facade before approval/export for Diwali packets only. This closes the new purchase/evidence digest invariant through existing packet endpoints; V1 packets keep their existing checks. No matcher, source-policy, receipt-parser or composer rules are changed.

New tables use separate metadata and explicit startup setup. Demo-owned foreign keys cascade only when the existing demo reset explicitly deletes their parent demo rows. Existing private rows and the prior collaboration implementation are preserved.

TDD RED/GREEN logs and actual gate command reports live under `docs/evidence/diwali/v2.1/`. Sponsor account setup and downloaded candidate Finch content are not V2.1 sponsor execution proof. V2.1 assigns Lyzr to review, not Builder; the previously provisioned Builder agent is not a verified reviewer.

## Audit repairs

Tests caught and corrected premature terminal persistence, wrong-task completion, missing post-dispatch deadline checks, message-budget overshoot, repeat-run status damage and stale approval through legacy routes. Four local inboxes now prevent duplicate actor execution. Snapshots have content-bound references and durable run-scoped records, so replacement of legacy evidence cannot change their meaning. The generated JSON schema also enforces each message type's route and payload; contextual identity/digest/deadline checks remain application validation. The schema hook follows the [Pydantic JSON-schema extension interface](https://pydantic.dev/docs/validation/latest/concepts/json_schema/#implementing-__get_pydantic_json_schema__). No dependency was added.

Two identical notice captures with different fetch times were initially misclassified as competing candidates in a new test. That test expectation was corrected against the existing CPSC adapter's deduplication behavior; an independent conflicting-facts test protects the review-only branch. Neither the original fixture nor the frozen five expected outcomes changed.

The baseline's API-surface note was persisted from pre-edit inspection and cross-checked against baseline HEAD. The original V1 SPEC digest was additionally protected using its baseline Git blob. These supplement baseline metadata; they do not regenerate the acceptance oracle.

Browser RED checks first established absent UI behavior. Test infrastructure then moved from an isolated dev server to an isolated production build after a dev-bundle SyntaxError; production checks exercise actual user actions and packet downloads. Controlled UI fault responses are labeled in the test; separate API tests inject a real coordinator fault and prove the original failure survives an explicit new fallback run. No fault fixture counts as sponsor execution.

## Verified handoff

`make diwali-check GATE=G3` passed on the tree recorded in `harness/diwali/handoff.json`: 228 backend tests, 11 frontend unit tests, 11 browser flows, lint, typecheck, build and smoke. All six isolated mutations triggered assertion failures. All 31 selected requirement IDs have unskipped executable evidence; D23 belongs to G5 and remains NOT_STARTED. Three pre-existing paid opt-in browser tests remain unexecuted and are not sponsor proof.

Protected baseline digests and dependency locks match. Task-owned ports 8000/3012 are closed; the pre-existing port-3000 server remains running. Credentials remain in ignored, owner-only `.env`. No commit, push, deployment or publication was made. G0–G3 are complete offline; full P0/release readiness and all live sponsor proof remain incomplete. Next target is G4, as specified in the machine-readable handoff.

## Authorized sponsor probes — November 15, 2026

The previous handoff above remains a historical G0–G3 snapshot. The owner subsequently requested BAND, Lyzr and Finch tests and authorized one Lyzr inference using existing credits only. AdaL remains deferred.

Pinned `band-sdk==8.1.0`: eight new packages in total; all pre-existing third-party lock entries remain identical. Frozen baseline/acceptance/expected files were not regenerated. Integration of this reviewed dependency extension into the lock-integrity verifier remains pending, so the earlier complete G3 report is not a claim about the changed lock.

Seven SDK-boundary tests cover addressed zero-retry POSTs, the actual custom adapter, platform sender/room/deadline authentication, redelivery and frozen product binding. The product-binding test failed with an unsolicited ResearchReport before the guard was added, then passed. The previous error-response fixture was corrected to the pinned generated SDK's complete error object; it had incorrectly used a string where the SDK requires code/message/request_id. A final typecheck caught payload-union narrowing and was repaired using the actual validated payload classes. SDK mocks remain offline tests.

Live BAND probes started the four existing private SDK identities with duplicate-host rejection, no model capabilities, single delivery attempts, no business POST retries and bounded timeouts. The initial request/reply was received and consumed by the manager reducer. A second probe used 18 messages for the five frozen synthetic purchases and preserved all expected outcomes, including Builder only on the positive case. Every connection reported successful cleanup. These are real transport and pure-handler results with recorded source inputs; they do not prove application database/UI integration. Exact probe scripts, source hashes and results are retained in `G4`. The live-tested adapter snapshot predates the type-only narrowing repair; no claim is made that an additional live run verified the later source bytes.

Lyzr's documented v2 configuration endpoint returned 405; its separately documented v3 endpoint returned 200. The existing agent remains a Builder with the earlier CaseResult output schema, not the required reviewer. One synthetic inference returned 200 in 3.29 seconds; CaseResult validation and independent assertions retained the PB23 exclusion. No POST retry or top-up occurred. This exhausts that specific one-call authorization. `G5/live-probe.json` contains sanitized results; raw provider configuration/response remain owner-only temporary files.

Finch's signed-in Brave download delivered Strategy Red Team v1 again. Every archive member matched the reviewed original, primary Markdown matched the listing fingerprint, and archive path checks passed. The local pin/tamper test passed. The candidate is neither the required event-authored Recall Evidence Auditor nor proof that a reviewer invocation loaded it. `G6/delivery-probe.json` records that distinction. No publication, wallet action or package execution occurred.

Full application provider gates remain incomplete. Next steps: finish G4 async coordinator/persistence/UI wiring and audited dependency extension; configure and integrate the constrained Lyzr reviewer; then author, review, publish with owner authorization, retrieve and invoke the required Finch package. Account/transport smoke tests do not replace these requirements.
