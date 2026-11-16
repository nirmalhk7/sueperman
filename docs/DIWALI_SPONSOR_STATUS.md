# Sueperman V2.1 sponsor checkpoint

Owner-selected V2.1/P1 responsibilities apply. GitHub default branch is `main` (verified November 15, 2026 Pacific). This checkpoint is **not full P0 or submission readiness**. Existing V1 functionality and original frozen fixtures/acceptance oracle remain binding.

## Observed live work

- **BAND:** one initial failed five-case application attempt (SDK delivery setting incorrectly allowed zero attempts); one repaired five-case run completed with 18 accepted messages and all five required outcomes. A subsequent combined PB23 case used four real BAND messages and one real Lyzr review, rejected the near-match and created no packet. Recorded source data remains visibly recorded. No fourth application run was attempted.
- **Lyzr:** created a private, tool-free Skeptic reviewer alongside the existing Builder. Exactly one newly authorized inference was validated and consumed in combined run `20820f89-e9cd-4c15-a15f-831fe51f9129`. Its runtime module digests still match this checkpoint; whole-tree digests differ after test/packaging changes. The one-inference authorization is exhausted. No credit top-up, retries or Builder replacement.
- **Finch:** authored and tested a MIT procedural auditor, SHA-256 `319cd67cfab3eafe2eefb37cbe36e2acced012cd1ed910398a2e4af386e3f86d`. Wallet binding is verified. Prepared free/public listing metadata in Brave. Upload is blocked by the ChatGPT extension's file-URL permission. Listing is not published; no delivered package or Finch-loaded inference exists. No wallet signature or payment performed.
- **Agent37:** wallet had $10 and automatic top-up was disabled. One default sandbox creation, one CPSC-only execution, one deletion and a 404 confirmation succeeded. Local normalization retained PB22 and excluded PB23. Deleted instance `941eq2xrjd` is not reusable. This is a consumed standalone worker result, **not integration into the BAND case snapshot**; application admission refuses enabled Agent37 until that integration is verified. Authorized lifecycle is exhausted.
- **AdaL:** video metadata validator implemented and tested, including strict duration below 120 seconds. No actual AdaL project, real integrated footage or exported submission MP4 exists. Validator success never establishes AdaL proof.

Sanitized receipts: `docs/evidence/diwali/sponsors/G4`–`G8`. Local mocks never count as live execution. Existing `.env` remains ignored/private; only the new reviewer ID was persisted. Live flags were not persistently enabled.

## Acceptance accounting

| Criterion | Executable evidence / current behavior | Remaining limit |
| --- | --- | --- |
| R01 | Full offline regression, lint, types, build, smoke/browser and container checks recorded below | Three paid opt-in V1 browser checks remain unrun |
| R02 | Five golden outcomes; exact PB22, rejected PB23, unknown-model question | Coverage limited to supported notices |
| R03 | Four actors, durable intent, authenticated BAND receipts and actual consumption; five-case plus combined captures | Capture hashes retain their original tree attribution |
| R04 | Agent37 owned create/exec/result/delete/404 receipt; worker DNS, ownership, malformed-result tests | Case snapshot/BAND integration incomplete |
| R05 | V2.1 supersedes AdaL reviewer role; tested video validator | Actual AdaL editing/export missing |
| R06 | Reproducible authored MIT package, tamper/path/size/license checks | Publish, retrieve exact bytes, validate delivery and invoke with loaded digest |
| R07 | Strict advisory Lyzr reviewer, actual one-call consumption; deterministic Builder retained | Finch-loaded inference not yet authorized/performed |
| R08 | Closed schemas, URL/DNS boundaries, adversarial advice and authoritative matcher tests | No general source or model accuracy claim |
| R09 | Missing purchase fact stays unknown; allowed public questions limited/filtered | No inferred private identifiers |
| R10 | Product/evidence digests, stale approval tests and recorded runtime module hashes | Full integrated release capture missing |
| R11 | Duplicate, conflicting, late, wrong-sender and unregistered paid-task tests; durable invocation ledger | Real outage/redelivery fault injection not performed |
| R12 | Offline timeout, startup failure, restart, malformed reply and one-attempt boundary tests | Failed external outcomes remain failed/unknown; no automatic replay |
| R13 | Exact synthetic admission, minimized reviewer projection, public-only worker and sanitized receipts | Live adapters remain operator-only |
| R14 | No-key local workflow; distinct transport/source/reviewer labels; startup never mislabeled local | Offline tests do not prove sponsor execution |
| R15 | Zero automatic retry/reconnect, per-task/run/message/inference caps; tests isolate local credentials | Provider dollar caps not enforceable; no deployed budget proof |
| R16 | Additive persistence, V1 parity and existing database tests | Older incompatible alternate-runtime DB conversion remains out of scope; no destructive migration |
| R17 | Existing P1 monitoring/readiness and review/approve/export browser checks | Complete five-sponsor application trace missing |
| R18 | Preserved source history; actual video metadata checks | Real footage, AdaL export, experiment/usability evidence and final release/public access/submission audit incomplete |

## Verification and TDD limits

Actual commands/results are retained with checkpoint artifacts. New G6/G7/G8 initial RED logs include missing-module/import failures and do not establish behavioral RED for every initial function. Later safety repairs have observed behavioral RED/GREEN evidence. Strict historical TDD compliance is therefore incomplete; no claim that every line followed a valid RED cycle. Frozen expected outputs and product requirements were not weakened to repair checks.

Container preflight first reproduced missing frozen manifest, then a non-root permission failure. The image now ships the public manifest and searchable parent directories. Container smoke exercises synthetic admission inside the image without credentials. Browser container output uses a unique per-project path to preserve historical captures.

Final verification (serial run, no source/configuration change):

- `make diwali-check GATE=G3` — exit 0; G0, G1, G2, G3 PASS; all six deliberate mutations caught.
- Its required `make test` — 360 backend tests passed, 12 frontend unit tests passed.
- Its required `make lint`, `make typecheck`, `make build`, `make smoke` — all exit 0; Python types cover 61 source files.
- Its required `make e2e` — 11 passed; three paid opt-in checks skipped and explicitly unverified.
- `make container-test` — exit 0; production image checks plus one browser workflow passed. Original recordings remain unchanged; this run's recording is retained under `sponsors/verification/container-browser`.
- Image synthetic-admission diagnostic — observed missing-manifest RED, then permissions RED, then GREEN with no credentials or live calls.
- Final source diff whitespace check passed. TestClient emits the existing Starlette/httpx deprecation warning.

Final tested source tree: `0a424226b5bfcdbacd2282426c9d3d572956e236bbe1368cff64189e74fda8c1`. The first full run detected source edits; the second exposed missing admission provenance coverage; the concurrent container/full-suite run hit the unchanged P1 browser build timeout. Their logs remain retained. The final serial run passed without weakening the checks.

## Exact next steps

1. In Brave, enable ChatGPT extension **Allow access to file URLs**, or select the five reviewed files in `/tmp/sueperman-finch-upload` manually. Finish preparing the listing; owner handles any wallet signature/payment. Publication authorization already exists; do not ask for MIT/listing authorization again.
2. After actual publication, retrieve the package through Finch. Record listing URL/version, actual archive digest and delivery metadata. Validate actual archive layout rather than assuming the platform preserves ZIP bytes.
3. Request a fresh explicit allowance for at most one Finch-loaded Lyzr inference. Existing one-call allowance is exhausted. Do not claim Finch proof from upload/local package alone.
4. Implement Agent37 result injection into the frozen case snapshot using behavior-first tests. Current standalone live result proves lifecycle only. A new paid lifecycle requires fresh bounded authorization; never reuse the deleted instance.
5. Capture actual integrated footage, perform AdaL editing/export, verify playable MP4 with audio and duration strictly below 120 seconds, complete experiment/usability and release checks. Deployment/submission require their own authorization.
