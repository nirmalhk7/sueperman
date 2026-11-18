# Live purchase workspace verification

User scope: remove public demo functionality and references; retain internal replay endpoints, fixtures and historical evidence; replace the case workflow with three live roles using saved sponsor credentials. Authorized verification spending limit: $1 total. User approved recording an audited baseline migration while preserving the original baseline and fixtures.

## Result

Public workspace imports purchases and starts live-only checks. Sample/reset/mode controls and simulated sign-in are removed; old sign-in bookmarks redirect home. Synthetic stored purchases and historical recorded runs, opportunities, packets and team cases are excluded from public presentation. The animated role explanation remains labeled “How it works.” Internal demo/replay endpoints and their tests remain available.

Live team uses Agent37 Scout, separate saved Lyzr Reviewer and Builder profiles, and authenticated addressed BAND handoffs. No AdaL or Finch execution is claimed. Scout runs a pinned public CPSC lookup inside a task-owned sandbox and deletes that sandbox afterward. Merchant/order details and credentials never enter worker commands or role messages. Exact identifiers and supported official conditions remain application-owned gates. Unknown, ambiguous, unsupported or unavailable evidence cannot yield an approved case. Reviewer citations/identifiers and Builder findings are validated before consumption.

Each intent is persisted before dispatch and each result before consumption. Tasks bind case, revision, evidence, sender, recipient and deadline; duplicate deliveries cannot repeat provider execution. Per run: one Scout execution, at most two Lyzr requests and three addressed tasks; no automatic inference retry. Source changes revoke approval/export. Approval/export refresh current official evidence without another paid role call. Only local review can unlock Markdown export; nothing submits a claim externally.

Local runtime: [UI](http://localhost:3001), API localhost:8000. Ignored `.env` now enables `COLLABORATION_LIVE_ENABLED`; saved credentials were preserved. Restarted API configuration validates and health returns 200.

## Live account evidence

[Sanitized observed result](../output/live-workspace-live-verification.json): one real BAND/Agent37/Lyzr run using explicitly synthetic verification purchase facts, not an actual consumer purchase. All three roles completed; CPSC recall 26-792 was observed live. Export returned 409 before approval, approval 200, export 200 afterward. No Agent37 instances remained.

Measured Agent37 balance delta: $0.000105. Exactly two Lyzr inference calls were used. The saved inference endpoint did not expose their account charge, so the exact combined verification bill is unverified; no additional paid verification calls were made. Do not represent the Agent37 delta as the total charge.

## Requirements and executable checks

- Public UI contains no sample/reset/replay controls, hides synthetic purchases and recorded historical content, and retires simulated sign-in: `apps/web/tests/production-workspace.e2e.ts`, `demo-login.e2e.ts` — 7 passed directly; included in full isolated browser acceptance.
- Public ordinary checks never substitute recordings, reject synthetic inputs, bind fallback policy to idempotency; unavailable real team configuration returns 503: `services/api/tests/integration/test_public_live_runs.py`.
- Real-purchase team exact/excluded/missing/failure cases, confirmed answers, revisions, stale evidence and approval/export gates: `services/api/tests/collaboration/test_live_workflow.py`.
- Worker cleanup/privacy/output validation, role citations and invented identifiers, authenticated transport metadata, duplicates and actual SDK HTTP addressing: `test_live_providers.py`, `test_live_transport.py`, existing BAND bridge tests.
- Import/history persistence, correction, identifier confirmation, camera states, role keyboard behavior, bounded/reduced motion, live team board and local export: isolated production browser suite controlled at vendor boundaries, without paid calls.
- Existing additional-recall normalization, local evidence readiness and source monitoring: P1 browser harness.

TDD evidence: observed missing-feature failures for provider/transport/workflow modules; observed workspace row leak (2 versus 1); transport failed before sending because LiveWire lacked case_id; three adversarial Reviewer tests initially accepted invalid advice; disabled real team admission returned 200 rather than 503; historical synthetic live team rendered as a live case. Implemented fixes, then passing checks below. Existing model-mismatch browser assertions also caught lost observed/affected identifier explanation; restored it without weakening the assertions.

## Final commands and observed results

- `services/api/.venv/bin/pytest services/api/tests/collaboration services/api/tests/integration/test_public_live_runs.py -q` — 66 passed.
- `services/api/.venv/bin/pytest services/api/tests/diwali/test_ui.py -q` — 4 passed; production build succeeded; embedded public browser suite: 25 passed, 3 existing opt-in paid checks skipped. Test-only vendor boundaries prevent charges. [Browser log](../output/live-workspace-browser/public-acceptance.log).
- `services/api/.venv/bin/pytest services/api/tests/diwali/test_integrity_extensions.py services/api/tests/diwali/test_harness.py -q` — 37 passed. The full final suite also passed these nodes.
- `SENTRY_DSN='' services/api/.venv/bin/pytest services/api/tests -q` — 474 passed, 3 failed. [Full log](../output/live-workspace-api-regression.log). Two unrelated purchase-deletion tests expect an unregistered `/api/purchases/{id}/delete` endpoint; those untracked feature files were left untouched. P1 browser export request also encountered a local ECONNRESET before reaching the disposable server; isolated recheck passed: `SENTRY_DSN='' services/api/.venv/bin/pytest services/api/tests/p1/test_p1_browser.py -q` — 1 passed, containing all 4 P1 browser scenarios ([recheck log](../output/live-workspace-p1-recheck.log)).
- Frontend ESLint and `tsc --noEmit` — passed. `node --import tsx --test tests/*.test.ts` — 12 passed.
- `services/api/.venv/bin/ruff check services/api/app services/api/tests scripts` — passed. `services/api/.venv/bin/mypy --config-file services/api/pyproject.toml services/api/app` — passed, 67 source files.
- `git diff --check` — passed after removing trailing whitespace from generated browser logs. Responsive screenshot/keyboard/reduced-motion checks passed; final native preview shows the updated purchase workspace with no demo controls.

Broader repository verification remains incomplete while the two unrelated deletion tests fail. No claim that the entire repository or historic five-sponsor hackathon gates pass.

## Baseline and design audit

[Original baseline](../harness/diwali/baseline-before-live-workspace.json) preserved byte-for-byte. [Migration audit](../harness/diwali/live-workspace-baseline-audit.json) records the six required workflow/UI/contract files and original/current hashes. Fixture/oracle hashes remain unchanged. Environment examples remain exact additive extensions. Unrelated pre-existing drift in `docs/v2-status.md` and `services/api/app/api/demo.py` was not blessed by this migration.

Preserved existing Consumer Test Lab visual design and animations. No new design suppressions. Existing narrow SFMono-Regular fallback exception remains documented in DESIGN.md and the prior Impeccable ignore; no broad font/file/rule suppression added.
