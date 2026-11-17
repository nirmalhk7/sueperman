# Issue #6 — approved recovery policy and acceptance map

Owner approved on November 17, 2026 Pacific: automatically resume only jobs durably queued before execution; interrupted execution with uncertain external effects stays partial and requires a fresh user action; interrupted public source watches resume on their next daily schedule without immediate retry.

## Execution semantics

- API admission persists queue intent in the existing run payload in the same transaction as the run. Team-answer revisions receive independent intents.
- Existing BackgroundTasks provide immediate dispatch; a one-second application poller also drains never-claimed intent. Both use the same atomic SQLite claim.
- A claim persists one attempt, an opaque owner, claim time and a 90-second lease before calling the executor. The domain run remains queued until its original executor starts. No database transaction spans provider execution in the dispatcher.
- A started job never becomes claimable again, even after lease expiry. Timeout, cancellation or unexpected execution failure marks unfinished work partial with a sanitized warning. Terminal domain outcomes are retained.
- Only well-formed version-1, unclaimed, zero-attempt queue intent resumes at startup. Legacy or malformed interrupted work follows conservative partial/failure handling; no invented provider result is created.
- Recovery is bound to a digest of non-secret provider flags/model names/budgets and application/recorded-source bytes. Changed configuration or code prevents execution; credentials and credential-derived hashes are not stored. Credential rotation does not itself authorize a new provider scope.
- A database-scoped OS lock permits exactly one application lifespan over an on-disk SQLite database. This is a single-host/single-worker design, not a distributed queue. Another worker fails startup rather than revoking live work.
- Claims serialize execution across run types and defer during in-flight source checks. Source monitoring already defers during queued/active investigation work.
- There is no new cancellation endpoint. Application shutdown cancels its queue worker; started unfinished work stays partial. A fresh request/idempotency key is required to try again after interruption. Reusing an old key returns its historical outcome.

## Public watches

Interrupted checking retains the user's enabled/disabled choice, clears the old lease, waits at least 24 hours from recovery, and revokes local approval. Disabled watches remain disabled. A later successful source read does not restore approval. Recovery performs no immediate network retry.

## Acceptance evidence

- `tests/integration/test_job_recovery.py`: deterministic/local/team admission lost before dispatch, restart execution once, repeated restart without repeated events, crash after claim, changed provider flags, malformed intent, competing application lifespans, concurrent deliveries, exception and cancellation after an observed effect.
- `tests/p1/test_monitoring.py`: interrupted watch opt-in/opt-out, daily deferral, source recovery and persistent export revocation, alongside existing race/source-change tests.
- `tests/diwali/test_ui.py::test_browser_recovered_work_guidance`: real Chromium rendering of controlled API recovery metadata and uncertain-outcome warning, with no approve/export action. This controlled browser response is UI verification, not a live interrupted-provider capture.
- Existing complete app/browser/regression checks remain required after final changes. Targeted green does not establish full completion.

## Current evidence and limits

Behavioral RED logs: restart queue recovery (seven failed), watch opt-in preservation (one failed), malformed job startup (two failed), and missing browser guidance (one failed). Targeted backend subsequently passed 26 checks; targeted browser guidance passed once. Final results are recorded below; independent closure review must inspect them before closing the issue.

The actual frozen-integrity audit also reports pre-existing differences in `docs/v2-status.md` and `services/api/app/api/demo.py`, plus new additive hooks in protected team files. These are not a passing release gate. The owner explicitly approved exact additive audit hooks in controller.py and ledger.py on November 17, 2026 Pacific. The manifest now reconstructs every frozen original byte for those files and the already-allowed team API; 28 integrity/tamper checks pass. The frozen baseline and oracle were not regenerated. The two pre-existing differences remain release issue #3 work.

## Independent review

A separate subagent initially reproduced two implementation defects: wrong-type recovery counters could abort startup, and changing reviewer/skill identity did not change the recovery binding. Both received explicit regression failures before repair. The reviewer then independently ran the final focused suite: 70 passed, exit 0, 9.26 seconds. It inspected actual subprocess-exit, answer-recovery, timeout, source-drift, exclusion, privacy, and watch tests, plus the rendered interruption screenshot. It found no remaining introduced blocker and conditioned closure on final serial verification.

The scaled timeout test shortens the real asyncio deadline while asserting the production 90-second bound; it does not wait 90 seconds. Subprocess-exit tests observe a durable file effect as a controlled external-effect stand-in; no paid provider is invoked. Browser recovery responses are controlled UI inputs, while API recovery tests exercise the real persisted jobs and actual application lifespans.

## Final cancellation repair and serial verification

A last behavioral regression found that cancelling the real coordinator left its task pending and case active while its parent became partial. `case-cancellation-red.log` records the failure. The repair now marks the parent partial, cancels unconsumed tasks, and closes active cases in the same transaction. `case-cancellation-green.log` records 71 focused passing checks. A separate subagent independently reran the real cancellation and terminal-late-message checks: two passed, exit 0. It confirmed the pending-task and DONE-case guards reject later writes and found no further introduced blocker.

Final commands on the repaired source, run serially with live provider flags off and disposable application servers:

| Command | Actual result |
| --- | --- |
| `make test` | Exit 0; 415 backend tests and 12 frontend unit tests passed, including isolated browser-backed backend acceptance. Existing Starlette warning remains. |
| `make lint` | Exit 0; Ruff and ESLint passed. |
| `make typecheck` | Exit 0; mypy (62 source files) and TypeScript passed. |
| `make build` | Exit 0; production Webpack build passed. |
| `make smoke` | Exit 0; synthetic exact/negative workflow passed. |
| `make e2e` | Exit 0; 13 passed, three paid opt-in checks skipped and unverified. |
| `make container-test` | Exit 0; production containers, same-origin workflow, local export, non-root users, environment exclusion, and one container browser workflow passed. |

Commands, exit codes, durations, output paths and matching before/after source digests are in `final-after-cancellation/report.json`; stdout/stderr are retained alongside it. The previous complete candidate's checks are preserved under `final/` and do not replace verification of the cancellation repair. Earlier `full-tests.log` retains the audit-extension failure before the approved manifest update. Initial targeted iterations are historical, not final verification.

The actual full frozen audit still reports only the two pre-existing differences in `docs/v2-status.md` and `services/api/app/api/demo.py`. Their HEAD hashes already differed from the frozen hashes before issue #6 edits. No full G0/G3/release PASS is claimed; resolving those prior-scope differences remains issue #3 work. No deployment, paid provider invocation, source publication or human usability study is established by these checks.

Text logs preserve terminal content with trailing whitespace normalized for diff hygiene. Raw captures before whitespace normalization are retained locally under `/tmp/sueperman-issue6-raw-evidence/`. Runtime/test/configuration bytes are unchanged by this evidence-only cleanup.
