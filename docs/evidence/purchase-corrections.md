# Purchase corrections, issue 4

Agreed scope allows explicit corrections to brand, model number and UPC across CSV and extracted receipts. A queued or active investigation of the purchase blocks correction. Omitted optional fields retain their values.

Each correction creates a product revision under the original purchase ID. Prior product facts, opportunities, evidence and case snapshots retain their IDs. Current imports and investigations select the active product revision. Identical duplicate corrections return the same revision; conflicting requests against a superseded revision return 409. SQLite admission locks serialize corrections and investigation starts.

Superseded opportunities are marked stale. Their packets lose approval and cannot be approved or exported again. Team draft routes also reject superseded products. The dashboard offers correction review and directs the user to investigate again. Historical opportunity details explain stale results. New results receive independent drafts requiring renewed local approval.

Demo reset retains all revisions of purchases referenced by historical team cases. Corrected retained demo purchases receive a history import key, allowing fresh canonical fixtures during explicit reset.

## Acceptance and TDD evidence

- Exact PB22 to excluded PB23 and back, preserved historical facts/evidence, local approval revocation, renewed draft/export and identical duplicates are exercised in both deterministic and local modes by test_purchase_corrections.py.
- Separate tests cover explicit confirmation, active agent runs, active team runs, superseded team draft/export and canonical demo reset after correction.
- corrections.e2e.ts exercises correction controls, stale history guidance and renewed review/export.
- Initial API tests failed against missing correction behavior. Team activity and team export tests subsequently failed against missing guards. Demo reset reproduced an AttributeError, then an incorrect seeded model, before both repairs passed.
- Browser acceptance initially failed because correction controls were absent. Setup origin and navigation-wait failures were corrected separately.
- The integrity check initially rejected the added team API guards. Its extension manifest now records exact additive byte ranges and digests; reconstruction still matches the frozen baseline. All 20 integrity/tamper tests passed.
- SENTRY_DSN='' services/api/.venv/bin/pytest -q services/api/tests/integration/test_purchase_corrections.py — 7 passed (including the final legacy-confirmation guard).
- make lint typecheck — passed after final source changes.
- make build — passed. Subsequent source changes were confined to backend demo reset and its tests.

- SENTRY_DSN='' make test — 366 backend and 12 frontend unit checks passed before the final legacy-confirmation guard. Its affected correction and receipt-confirmation checks were rerun afterward, 11 passed.
- API_URL=http://127.0.0.1:8000 WEB_URL=http://127.0.0.1:3000 make smoke e2e — passed smoke and 12 browser checks. Three opt-in live-provider checks skipped.
- Legacy receipt confirmation reproduced an unauthorized edit of a superseded revision before its new 409 guard. Original receipt behavior and correction tests passed afterward.
- Existing Starlette/httpx deprecation warning remains.
- Final-source backend rerun: SENTRY_DSN='' services/api/.venv/bin/pytest -q services/api/tests --ignore=services/api/tests/diwali/test_ui.py --ignore=services/api/tests/p1/test_p1_browser.py — 364 passed. The three browser-backed backend checks had passed in the complete 366-check run; the subsequent guard only rejects legacy confirmation of superseded receipts.
- git diff --check — passed. Generated browser captures and logs restored to their original tracked versions.
