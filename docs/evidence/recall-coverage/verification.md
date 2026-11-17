# Issue 5 verification

Bounded source and restriction decisions were recorded in scope.md before runtime changes. sources.json pins the captured public Baseus row; live-check.json records a separate fresh public adapter/matcher lookup. deferred-iniu.json retains the inconsistent record that was excluded from coverage.

TDD observations:

- Initial Baseus tests failed on the unsupported replacement normalizer, missing full-serial import, and absence of a verified packet. After the serial field, source pin and structured restriction, four tests passed.
- Public watch admission and fetch tests failed until Baseus was registered for monitoring. Six tests then passed, including conflicting official duplicate records and export revocation after an upstream description change.
- A suffix-only value and an unrelated serial ending D initially passed incorrectly. The added source-reviewed SN-prefix restriction made both exclusions pass.
- Exact models, every ASCII numeric suffix, uppercase D, excluded A/lowercase d, missing/empty serial, model punctuation/suffix differences and unknown additional restrictions are exercised by test_baseus.py.
- Prior five-product behavior, purchase correction revisions, and approval invalidation remain covered by the full regression suite.

Actual final-source commands:

- SENTRY_DSN='' services/api/.venv/bin/pytest -q services/api/tests/p1/test_baseus.py — 6 passed.
- make lint typecheck build — all exit 0.
- SENTRY_DSN='' make test — exit 0, complete backend suite and all 12 frontend unit checks passed, including isolated browser-backed backend checks.
- API_URL=http://127.0.0.1:8000 WEB_URL=http://127.0.0.1:3000 make smoke e2e — exit 0, smoke passed, 12 browser checks passed. Three opt-in live-provider browser checks skipped.
- PYTHONPATH=services/api services/api/.venv/bin/python /tmp/sueperman-baseus-live-check.py — exit 0. Its equivalent steps are CPSCRecallSource(reviewed_notices=True).search with brand Baseus, select reference 25-248, then match synthetic model BS-30KP365 with SN-SYNTHETIC-D, SN-SYNTHETIC-A, and no serial. Results were verified_match, rejected, needs_review.
- git diff --check — exit 0.

The new notice's import/run/evidence/local review/export acceptance uses recorded HTTP responses. Fresh live evidence covers public retrieval and matching. Existing Starlette/httpx deprecation warning remains. Generated historical browser logs/captures were restored after checking results.
