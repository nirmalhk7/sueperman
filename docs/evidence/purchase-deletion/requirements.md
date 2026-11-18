# Purchase deletion (#9)

Agreed scope: imported purchases remain until explicit deletion. Remove local purchase/product revisions, findings, evidence, cases, messages, drafts, approvals and source watches. Preserve unrelated purchases, findings, and synthetic demo records. Source caches contain public notices; provider usage counters remain aggregate operational records and are not refunded. Downloaded exports and provider-held records cannot be recalled locally.

Private accounts remain deferred under the owner's dummy-authentication decision (#8). This feature operates in the existing shared workspace; its confirmation explicitly says all demo users share the records. It does not claim private ownership enforcement.

Shared investigations require a current preview binding and separate per-deletion consent. This is not a global owner decision to remove shared histories automatically. Active investigations and checking watches block deletion. Other purchases/findings remain; drafts relying on removed history require a fresh check and approval. Newer independent provenance remains valid.

## Executable acceptance mapping

- Explicit confirmation, origin protection, current shared-scope consent, idempotence, demo preservation, active-work guards and unrelated records: `test_purchase_deletion.py`.
- Dependent-record closure and shared/partial/newer-independent provenance: `test_purchase_deletion.py`, `test_deletion_provenance.py`.
- Durable, atomic private deletion journal; missing/corrupt/wrong-lineage refusal; concurrent intent and generation binding: `test_deletion_journal.py`, `test_deletion_binding.py`.
- Pending intent before reads/restart/queued execution and delayed admission/watch writes: `test_purchase_deletion.py`.
- File-specific fresh import confirmation, delayed extraction/retry races, partial receipt imports and unreadable authority: `test_reimport_confirmation.py`; receipt regressions remain in `test_receipt_confirmation.py`.
- Older snapshots reapply current deletion history before publication, reject unavailable authority and preserve source/snapshot: `test_deletion_restore.py`; existing `test_storage_recovery.py` retains queue, quota, approval, retention and backup assertions.
- Desktop/mobile deletion and fresh import, plus separate shared-history consent: `apps/web/tests/deletion.e2e.ts` against task-owned disposable API/browser servers. Vendor requests are controlled test responses, not live provider proof.
- Required regression checks: `make test`, `make lint`, `make typecheck`, `make build`, `make smoke`, `make e2e`; durable deployment checks `make storage-test` and `make container-test` when Docker access permits.

## Retention and recovery

Private JSON journal holds only purchase UUIDs, import fingerprints, lineage/source identities and revisions. Keep it at its persisted canonical location on the durable data volume, outside public web files. Minimal tombstones remain while old recovery copies or delayed uploads may exist. Ordinary database snapshots cannot roll back this authority. Losing or corrupting it blocks recovery; this same-host deployment does not guarantee host-loss recovery. See `deploy/DURABLE_STORAGE.md`.

Normal backup expiry is seven days; the owner approved preserving the last valid recovery copy during an outage until a replacement succeeds. Restores reapply tombstones before workers or data access. Existing populated installations require an explicit stopped-app `python -m app.deletion initialize --database ...` migration; a missing established journal is never automatically reset. Legacy pre-policy snapshots need the verified current journal bound to the original source identity.

Re-uploading identical file bytes requires a fresh explicit confirmation after deletion. Another deletion invalidates old confirmation tokens. Receipt re-import reads the receipt again, including repeated confirmed uploads of previously deleted files; normal model usage limits apply. No automatic retry or refund is implied. Changed file bytes are a different import, not a content-identity guarantee.

No real user purchases were deleted during verification. Human usability (#2), external release evidence (#3), and private account isolation (#8) remain separate outstanding/deferred work.

Receipt re-import preserves surviving purchase identities and user corrections by matching the original immutable extraction facts to their original import indices. Reordered items are supported. Missing, changed, ambiguous or legacy facts refuse the automatic merge without writes, with guidance to review and upload a CSV containing only the purchases to add. The original per-item extraction facts and item count stay with that purchase and are erased with it; the journal retains no item contents.

Existing live-workspace UI and protected V2 files remain intact. Additions to `main.py` register deletion, retain per-item receipt import identity, and reconcile durable intent before workers/data access. The `claims.py` guard keeps approval/export blocked while explaining history deletion accurately. Storage restore adds current-authority reconciliation before atomic publication. Storage test fixture lifecycle changes stop the original app before starting a restored alias, preserving the one-worker-per-lineage rule and every prior assertion.
