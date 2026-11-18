# Issue #7 acceptance map

Approved scope: persistent single-host Compose using the existing data volume, daily backups and seven-day normal retention. Owner additionally approved preserving the last valid recovery copy during an outage until replacement succeeds, and marking unfinished restored jobs partial because post-snapshot execution is unknown. Paid usage after the snapshot requires reconciliation before enabling paid features. Dummy authentication and guidance-only evidence remain separate later issues; no private-account isolation or deletion reconciliation is claimed here.

| Criterion | Components | Executable evidence |
| --- | --- | --- |
| Supported durable deployment and recovery objectives | `compose.durable.yaml`, `deploy/DURABLE_STORAGE.md`, existing `demo-state` plus new `state-backups` | `make storage-test` uses a unique disposable project, recreates containers without removing volumes, and compares every stored table; runbook states daily RPO target, manual restore/no time SLA and host-loss limit. |
| Purchases, sources, approvals, jobs, watches and counters survive restart/redeploy | Existing SQLite schema, stable named volume, source-bound backup manifests | CLI WAL/all-row parity check and production recreation fingerprint; browser downloads restored approved draft with original SHA-256; quota/watch/job rows included. |
| Private consistent backups and safe restore | `app/storage.py`, non-root API image and backup service | Private files/dirs, no env copy, online committed WAL, corrupt/missing source, snapshot checksum, foreign keys/schema, no overwrite, companion files, concurrent restores, publication failure and deadline checks. |
| Daily scheduling and retention | Persisted manifests, operation/scheduler locks, CLI cycle/status/schedule | 24-hour boundaries, actual scheduler-process restart, source switch, corrupt/future snapshots, malformed names/error records, seven-day expiry, unknown artifacts preserved, source outage keeps last valid copy. |
| Restore current truth without replaying uncertain work | Restore reconciliation plus existing #6 guards | Original source executes a queued job after backup; restored old queue becomes partial and emits no new events. Interrupted source watch retains opt-in, waits daily and revokes related export even before scheduler activation. |
| Preserve migration boundaries | Read-only schema/version validation; new target only | Incompatible old collaboration schema refused by backup and by restore even with correct checksum/manifest counts; old source untouched. Missing additive tables are not silently rebuilt by the storage utility. |
| Preserve current product behavior | Existing app APIs and UI, paid flags off | Full `make test`, lint, types, build, smoke, normal E2E, production container acceptance, plus dedicated `make storage-test`. |

## Test-first observations

- `cli-red.log`: positive backup/restore CLI scenarios failed because the command was absent; no pytest import failure was used as completion evidence.
- `scheduler-red.log`: three daily/retention/history assertions failed before the cycle implementation.
- `names-red.log`: invalid timestamp name blocked scheduling, then repaired.
- `retention-assertion-red.log`: retention deleted an unexpected nested artifact; explicit assertion reproduced the loss before the non-file guard.
- `recovery-policy-red.log`: switching databases postponed the new source, a failed source removed the last old copy, and historical queue restoration allowed execution. All three observed failures preceded their repairs and the additional owner-approved policies.
- `restore-guard-red.log`: existing live target produced an uncontrolled error and another source's error poisoned selected-source status; both repaired.
- `error-record-red.log` and `manual-status-red.log`: malformed error metadata broke scheduling/status; strict validation and successful-backup cleanup repaired it. Independent review reproduced the same scheduler defect before its fix.
- `compose-red.log`: actual deployment command lacked the durable layout. `compose-first.log`: first production recreation, all-row restore and restored-approval browser workflow passed. This earlier capture does not replace verification of later hardening.

## Independent review

Reviewer identified source-history binding and failed-source retention loss, then malformed scheduler error metadata. Root wrote/observed regressions, obtained the two material restore/outage policy decisions, and repaired the defects. Final independent acceptance review and complete unchanged-source verification remain pending; targeted counts alone do not close this issue.

## Limits

No public deployment, provisioning, paid provider execution, off-host backup, encryption system, human usability session, or private-account isolation is established. Restoring an older database restores its old counters; provider-side accounting is not reconstructed. #9 must add deletion reconciliation before claiming deleted data cannot reappear after restore. The existing frozen audit differences in `docs/v2-status.md` and `api/demo.py` remain release issue #3, not a new storage implementation success.

## Recorded verification results and concurrency incident

The exact prospective issue #7 commit (base `a8309c4` plus the ten files in `isolated-snapshot.json`) has source digest `30b81597ea1bb4ea1b4812eba71913b5dbe1b0d8dd5aab812e98e4a62bb08765`.

`verified-acceptance.json` maps each mandatory command to its actual passing invocation on that digest:

- `make test`: 439 backend tests and 12 frontend unit tests passed; includes controlled P1 and local collaboration browser-backed checks.
- `make lint`, `make typecheck`, `make build`, `make smoke`: exit 0. Python types cover 63 source files.
- `make e2e`: 13 passed, three paid opt-in checks skipped and explicitly unverified.
- `make container-test`: production image/same-origin/non-root/environment-exclusion checks and one browser workflow passed.
- `make storage-test`: durable Compose recreation, all-row parity, source untouched, restored quota/watch/job state and one restored-approval browser download passed in the isolated snapshot. The snapshot source/configuration hashes remained unchanged and all ten patch-file hashes still match.

This is not a claim that every rerun passed or that one all-green aggregate invocation occurred. The first storage build ended with BuildKit EOF and the Docker socket disappeared. OrbStack was started; builder history showed no active failed-project build or containers before retry. The next storage acceptance passed, but another task created `workspace-design.e2e.ts` during that run, changing the broad source digest. Those logs remain under `storage-retry/`.

The managed worktree tool could not access the checkout, so a temporary Git archive of the original base plus only this issue's recorded files supplied isolated verification. Existing dependency environments were linked without copying credentials. Its supplementary full rerun had a P1 browser timeout and two browser failures caused by legacy hard-coded `localhost:8000` URLs reaching the other task's local API instead of the selected test port. That misrouted run sent demo-reset requests to the other local instance; it is excluded from passing evidence and was disclosed in the chat. No attempt was made to overwrite or undo the other task's state. The original complete passing test/E2E commands and isolated passing storage command all have the same candidate digest, and the common configuration hashes match.

`isolated-final/report.json` therefore honestly retains `checks_pass: false` for that particular aggregate run. `verified-acceptance.json` selects the actual successful commands and preserves all failed reports rather than relabeling them. No new tests, product rules, frozen oracles or source assertions were weakened to pass checks. Concurrent design files, generated dev type paths and their staging remain outside this issue's commit.

The two existing frozen-integrity differences remain `docs/v2-status.md` and `services/api/app/api/demo.py`, as before issue #7. No G0/G3/full release PASS is claimed.

## Final independent decision

A separate subagent independently inspected actual logs/reports, recomputed the isolated candidate digest, verified all ten patch-file hashes against root and snapshot, reviewed all eight successful command records, and visually inspected the restored approval screenshot. It found no missing issue #7 criterion and approved closure after a narrowly scoped commit matching that candidate. The isolated screenshot/video are retained under `output/playwright/storage-sueperman-storage-check-21238/`.

Text logs retain their substantive terminal output with trailing whitespace normalized for diff hygiene. Raw copies before normalization are retained locally under `/tmp/sueperman-issue7-raw-evidence/`. This evidence-only cleanup does not change runtime, test or deployment configuration bytes.
