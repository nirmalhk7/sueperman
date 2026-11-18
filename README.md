# Sueperman — Your consumer-rights agent

Import purchases, compare exact product identifiers with official recall evidence, inspect exclusions, review a local remedy draft, and export Markdown. The public workspace uses imported purchases and live checks; it does not substitute recorded demo results when a provider is unavailable. No external claim submission, money movement or legal advice.

This README describes source revision `9d00e97` and the recorded evidence linked below. It does not establish current availability of an external provider or deployment. Private accounts and ownership isolation are not implemented; records belong to the shared workspace. Use synthetic purchase details on shared deployments.

## Run locally

Prerequisites: Node.js 20.19+ (previously verified with 24.1.0), pnpm 11.25.0, uv, and network access for first dependency/runtime installation. Python 3.12 is installed automatically by uv when needed. On macOS, prerequisites can be installed with `brew install node pnpm uv`.

From repository root:

```sh
cp .env.example .env
make setup
make dev
```

Copy the example only on first setup; preserve an existing ignored `.env` and its credentials. Open http://localhost:3000. API health: http://localhost:8000/api/health. API docs: http://localhost:8000/docs.

Use **Upload purchases or receipt** to import a CSV, or **Take receipt photo** to choose a receipt image. CSV import needs no provider key. Receipt extraction needs a configured provider. Review extracted facts and explicitly confirm scanned identifiers before checking purchases. **Correct identifiers** creates a purchase revision rather than silently replacing prior findings.

**Check my purchases** starts the ordinary live check for imported purchases. **Investigate with agent team** beside a product starts the separate live team workflow. Provider flags default off, so a clean installation can import CSV but cannot complete an unconfigured live investigation. The UI reports unavailable/failed work instead of showing fixture positives. Removed sample/reset/mode controls and simulated login are not part of this public workflow; old login bookmarks redirect home.

If another app owns 3000, keep it running and use:

```sh
make dev WEB_PORT=3001
```

Open http://localhost:3001. This also configures CORS for that origin. Stop dev with Ctrl+C. Restart the backend after Python/configuration changes. The local development server binds to loopback. It has no authentication or private account boundary; do not treat the shared workspace as a private consumer service.

## Verify without live provider calls

These checks run from repository root:

```sh
make test
make lint
make typecheck
make build
make container-test
make storage-test
```

`make test` runs backend and frontend unit tests, including isolated browser harnesses that build copied frontend source and start disposable APIs with controlled responses at provider boundaries. It covers the public purchase workflow and six P1 browser scenarios. These software checks do not prove real provider execution or human usability. Docker/OrbStack is required for the two deployment checks; they remove only their own disposable projects and volumes.

With your own API/web servers already running, internal fixture checks remain available:

```sh
make seed
make demo
make demo
make smoke
```

These commands seed or reset the five synthetic fixture purchases through internal APIs; non-demo imports remain. They do not enable a public sample-data control. `make demo` asserts the golden results: five products, one matched recall, one rejected near-match, one missing-model review, one product without recall, one fictional settlement, and exactly one real-recall draft. Repeating imports and run triggers preserves idempotency.

Bare `make e2e` expects an already prepared API/web test environment. The normal browser suite requires controlled live-source responses; it is not an offline check against a default, unconfigured `make dev` server. Use the isolated browser setup included in `make test`, or provide the prepared environment and both addresses, for example `make e2e API_URL=http://localhost:8000 WEB_URL=http://localhost:3001`. P1 and restored-storage scenarios have their own harnesses. Three paid/live opt-in probes are excluded unless explicitly enabled; skipped probes are not passing live evidence.

The [purchase-deletion verification report](docs/evidence/purchase-deletion/report.json) records the tested candidate behind `9d00e97`: 523 backend tests, 12 frontend unit tests, 28 browser checks, three skipped opt-in probes, three container browser checks, one restored-storage browser check, and all eight recorded engineering commands exiting zero. Browser recordings/screenshots accompany that evidence. Container checks retain synthetic matching/export through APIs while testing public deletion/re-import in Chromium. Storage checks compare all database rows and the original synthetic export through APIs; the public browser correctly hides the historical demo draft and displays the retained imported purchase. This is not a real-provider or public-browser live export demonstration.

Production builds use `next build --webpack`, the checked-in build script. Development keeps Next's default bundler. The installed Starlette TestClient emits an existing HTTPX deprecation warning; it remains visible in recorded results.

## Configure live providers

Provider flags default off. Keep keys server-only in the ignored `.env`; never put them in browser configuration or commit them. Inspect `/api/health` for the ordinary provider configuration, and the relevant workflow error when a live team is unavailable. Enabling a flag does not establish a working credential, available balance, current source, or successful live run.

- **CPSC:** set `CPSC_LIVE_ENABLED=true`, then restart the backend. Ordinary public checks use live official-source data without recorded fallback. NEWDERY notice `26-792` supports exact model `ZHX-PB22`. With `P1_ENABLED=true`, reviewed mappings also cover Flaunt `26-610` (`E33A`), iStore `25-390` (`IST-09991/W05`), and Baseus `25-248` (`BS-30KP365`). Reviewed record changes and unsupported restrictions require review; this is not comprehensive recall coverage. The mappings are in `services/api/app/p1/normalizers.json`. `scripts/live_cpsc_check.py` is a separate explicit live public-read diagnostic.
- **Live agent team:** set `COLLABORATION_LIVE_ENABLED=true` and configure the server-side Agent37, separate Lyzr Reviewer/Builder identities, and addressed BAND actor credentials listed in `.env.example`. The current workflow uses Agent37 Scout, Lyzr Skeptic/Builder, and authenticated BAND handoffs; deterministic application gates retain authority. It does not execute Finch or AdaL. Missing configuration returns an explicit unavailable response. The workflow persists intent/results, bounds each task, performs no automatic paid inference retry, and deletes its task-owned Scout sandbox. See [live workspace verification](docs/live-workspace-work.md) for the implemented boundaries and recorded account evidence.
- **Bright Data:** `BRIGHTDATA_ENABLED=true` plus `BRIGHTDATA_API_TOKEN` enables bounded research of supported CPSC-linked manufacturer pages through the Python MCP adapter and `npx @brightdata/mcp`. Only `search_engine` and `scrape_as_markdown` are exposed. The adapter treats returned envelopes as inert evidence and has a 75-second research deadline within the 90-second investigation bound. Failure retains authoritative CPSC facts and reports partial work.
- **Receipt extraction:** Gemini uses `GEMINI_ENABLED=true` and `GEMINI_API_KEY` for supported PNG/JPEG/PDF files. Its configurable default is `gemini-2.5-flash-lite`; the historical account verification used an override after that default was unavailable to the account. This README makes no current model-availability claim. OpenAI photo reading uses `OPENAI_RECEIPT_ENABLED=true` and `OPENAI_API_KEY`, independently of decision routing. `OPENAI_RECEIPT_MODEL` defaults to `gpt-6-luna`; PDFs retain the Gemini path. Review all extracted identifiers before matching.
- **OpenAI decision role:** `OPENAI_ENABLED=true` plus `OPENAI_API_KEY` enables the bounded advisory decision router. `OPENAI_DECISION_MODEL` defaults to `gpt-6-luna`. Only sanitized hard-gate status/missing-condition names are sent, with a strict four-choice schema, `store:false`, and no tools. Refusals, malformed output and failures retain deterministic rules; model output cannot override hard gates. `OPENAI_MAX_CALLS_PER_RUN` defaults to three.
- **Settlements:** `SETTLEMENT_LIVE_ENABLED=true` enables the manually reviewed Kroger case for exact Kroger merchant records. Current administrator/court-linked source checks and reviewed document hashes are required. Personal class membership, geography, exclusions and proof remain uncertain; any packet is preparation-only. Changed or unavailable sources revoke old approval/export.
- **Sentry:** backend `SENTRY_DSN` and frontend configuration use separate projects. See [Sentry setup](docs/sentry-setup.md) for privacy filters and recorded local delivery/source-frame evidence. Production delivery and source-map publication need their own verification.

Receipt photos use a rear-camera preference on supporting mobile browsers; desktop users can select saved JPEG/PNG files. Physical camera behavior has not been established by automated browser tests. OpenAI image handling orients/resizes to a maximum 1600-pixel side and strips EXIF; input is capped at 10MB/20 megapixels. Requests use `store:false`, no tools/retries, and a 1,024-output-token cap. `OPENAI_RECEIPT_DAILY_LIMIT` defaults to 10 attempted calls per UTC day per database. Failed calls consume attempts. This application cap is not a provider billing cap, and an ephemeral database can reset it. OCR can fail or omit unreadable information; CSV remains available.

Repeated receipt imports normally reuse existing extraction without another model request. Deleting a purchase changes that behavior: importing the same file again requires fresh explicit confirmation, and receipt files are read again with normal usage limits. A subsequent deletion invalidates the earlier confirmation. Partial receipt re-import matches immutable original item facts to preserve surviving purchase identities and corrections, including reordered OCR output. Missing, changed, ambiguous or legacy alignment refuses the merge without changing survivors and guides the user to upload a CSV containing only the purchases to add. Repeated confirmed uploads of a previously deleted receipt can incur another read; no automatic retry or refund is implied.

## Source watches and evidence preparation

For a trusted local instance, enable these settings in the existing ignored `.env` and restart the backend:

```dotenv
P1_ENABLED=true
CPSC_LIVE_ENABLED=true
P1_MONITOR_ENABLED=true
P1_MONITOR_POLL_SECONDS=60
```

On a supported recall's evidence page, **Enable daily source checks** opts into a fixed 24-hour watch. Up to five watches can be active; checks defer during investigations. Source changes or unavailable sources revoke approval and retain history. Interrupted checks retain the user's opt-in, clear their old lease, and wait at least another 24 hours after recovery; they do not retry immediately or restore approval. Disabled watches stay disabled. The app must be running for checks to execute.

Recall drafts provide source-bound, guidance-only preparation steps and **Evidence readiness**. The checklist records only what the user says is ready locally; it does not upload or verify evidence, attest disposal, supply a declaration, establish eligibility, or submit a claim. Labels distinguish required, conditional/unknown and optional organizer tips. For example, iStore's optional receipt is not required proof, and missing Baseus order information does not establish that a conditional photo is required. Product, evidence, policy or checklist changes require renewed local review/approval. Export labels readiness as self-reported.

`make test` runs all six controlled P1 browser scenarios without skips through `services/api/tests/p1/test_p1_browser.py`. Bare `make e2e` excludes that file because the controlled source server is required. See [preparation acceptance](docs/evidence/preparation/requirements.md), [its verification report](docs/evidence/preparation/report.json), and the historical [P1 status](docs/DIWALI_P1.md); older checkpoint counts/recovery descriptions are not the current runtime contract.

## Persistence, recovery and deletion

Investigation admission durably queues intent in SQLite. Immediate dispatch and the application poller share an atomic single-owner claim. Only well-formed, never-started work with matching code/configuration may resume automatically. Claimed/interrupted work with uncertain external effects remains partial and needs a fresh user action; it is never automatically replayed because a lease expired. Changed recovery bindings also prevent automatic execution. This is a single-host, single-worker queue, not a distributed scheduler. See [approved recovery policy](docs/evidence/job-recovery/policy.md).

The supported durable deployment is [persistent Docker Compose](deploy/DURABLE_STORAGE.md), using a persistent data volume, consistent daily SQLite snapshots, private backup files, and an operator restore into a new database filename. Normal retention is seven days. During an outage, the last valid recovery copy is preserved until a replacement succeeds, even if older. All unfinished restored investigations become partial rather than repeating uncertain calls; reconcile post-snapshot paid usage before re-enabling paid features. Same-host volumes do not protect against loss of the host or disk. App Platform storage remains explicitly ephemeral unless separately migrated.

Imported purchases remain until explicit deletion. **Delete purchase** shows the local removal scope and requires confirmation; shared investigation history requires its own current preview and separate consent. Active investigations/checking watches block deletion. Associated product revisions, findings, evidence, cases, messages, drafts, approvals and watches are removed. Other purchases/findings and synthetic fixture records remain; retained drafts that lose required provenance need a fresh check and approval. Newer independent evidence/approval stays valid.

A private deletion journal records minimal purchase identifiers, import fingerprints and recovery metadata outside ordinary database snapshots. Restore and startup reapply current deletion records before workers or data access, preventing an older backup or delayed import from silently recreating records. Missing/corrupt/mismatched authority fails closed. Keep the journal at its persisted path on the data volume while old recovery copies or delayed imports may exist; do not replace it with an older or empty copy. Existing populated databases need explicit stopped-app initialization, and legacy snapshots require a verified current authority; follow the runbook. Only one app worker can own a deletion lineage, including restored aliases.

Deletion does not recall downloaded Markdown, erase provider-held records, or refund aggregate usage counters. Public-notice caches are separate from purchase-private records. This remains a shared workspace, not private ownership enforcement. See [deletion scope and acceptance](docs/evidence/purchase-deletion/requirements.md).

## Internal replay and historical evidence

Internal demo/replay endpoints, frozen five-case fixtures and their acceptance oracle remain available for deterministic software checks. They are hidden from the public presentation: synthetic purchases and recorded historical runs/opportunities/packets/team cases do not become live public results. `POST /api/collaborations` still supports one existing product ID and `mode: "replay"` for internal deterministic team checks; `COLLABORATION_PUBLIC_DEMO=true` restricts that replay path to synthetic records. Public **Investigate with agent team** instead requests `mode: "live"` on an imported product.

Case revisions, task intents/results, events, evidence snapshots and approval bindings persist additively. Fact/evidence/rule changes invalidate approval before export. Team drafts use `/api/collaborations/{id}/claim-packet`, `/approve-local`, and `/export`; ordinary opportunity/packet APIs remain available. See [historical V2 acceptance](docs/v2-status.md) and [current live workspace implementation](docs/live-workspace-work.md) to distinguish old replay checkpoints from the current team workflow.

Historical observations are retained with their original scope:

- November 13, 2026 UTC: [live CPSC exact/near-match read](docs/evidence/live-cpsc.json), [Gemini receipt extraction](docs/evidence/p1-gemini-api-live.json), [bounded OpenAI decision request](docs/evidence/p1-model-live.json), [Kroger primary-source verification](docs/evidence/p1-settlement-live.json), and [public receipt-camera observation](docs/evidence/receipt-camera-public.json). These are dated observations, not checks of current provider/model/deployment availability.
- [Earlier sponsor checkpoint](docs/DIWALI_SPONSOR_STATUS.md) and [sponsor evidence](docs/SPONSORS.md) retain BAND, Lyzr, Finch, Agent37, Bright Data and deployment history. Statements that Agent37 integration or the public team were still unimplemented describe those checkpoints.
- The later live workspace implementation recorded with commit `be781c8` on November 17, 2026 Pacific includes [one real BAND/Agent37/Lyzr team run](output/live-workspace-live-verification.json) using explicitly synthetic verification purchase facts. It observed CPSC `26-792`, blocked export before local approval, allowed export afterward, and left no task-owned Agent37 instance. It used two Lyzr calls. The reported `$0.000105` balance delta covers Agent37 only; the combined bill was not verified. No Finch or AdaL execution is claimed.
- The previously recorded public deployment address is [Sueperman on DigitalOcean](https://sueperman-6t4xk.ondigitalocean.app). The November 17, 2026 Pacific [release public-access audit](docs/evidence/release-9d00e97/public-access.json) found the old hostname unavailable: home/health requests failed DNS resolution, and the recorded public DNS check returned NXDOMAIN. Do not present that address as an available demo. The repository was publicly readable in the same audit. Use the tested local/persistent Compose setup for a walkthrough; no replacement deployment is established here. Historical deployment instructions remain in [deploy/README.md](deploy/README.md).
- The editable HyperFrames commercial and rendered MP4 remain in [output/sueperman-film](output/sueperman-film/README.md). They are not AdaL proof. Analytics database integrations remain outside the implemented scope.

## Evidence, privacy and release limits

The five internal fixture purchases are synthetic. CPSC `26-792` is a recorded government notice with source URL/time/raw hash in `demo/PROVENANCE.md`; the internal five-row settlement is fictional. Recorded/controlled software checks must not be described as live source or sponsor execution. Real settlement evidence remains distinct and personal eligibility stays unconfirmed. No payout balance or guarantee is presented.

SQLite stores purchase/product facts, findings, source evidence, assessments, drafts, runs and ordered events. Receipt imports also retain original per-item extraction facts/count for safe partial re-import; deleting that purchase removes them. Raw receipt files are processed in memory rather than kept as application records, although multipart handling may spool to the OS temporary directory. Public CPSC caches live in ignored `uploads/`, outside the webroot. Privacy filters minimize receipts/credentials in logs and telemetry; provider-held records remain governed by the providers. Local readiness/approval never supplies missing names, signatures, photos or serial numbers or attests disposal.

Four real human usability sessions remain outstanding; agent reviews and automated replay pilots do not count as participants or demonstrate a human improvement. See [current protocol](docs/evidence/diwali/usability/protocol-current.md) and [software preflight scope](docs/evidence/diwali/usability/review-03010a6.md). Private account isolation remains deferred. Full release/submission readiness still requires the outstanding sponsor/package/video, real footage, human evidence and public-access checks. No new live run, external publication, deployment, or submission is established by the local engineering checks.

## Troubleshooting

- Missing `uv`/`pnpm`: install prerequisites and rerun `make setup`. Setup downloads the locked environment and Chromium; task-specific `/tmp` runtime/cache paths may need rebuilding after OS cleanup.
- Port conflict: keep unrelated servers running, choose another web port, and ensure the backend's port 8000 is free.
- API unreachable: use the host/origin configured by `FRONTEND_ORIGIN`. Make defaults to `http://localhost:<WEB_PORT>`. `API_URL` or `NEXT_PUBLIC_API_BASE_URL` selects the API address; an explicitly empty browser API base uses same-origin `/api`.
- Provider unavailable: inspect configured flags/keys and the workflow error. Public imported-purchase checks never automatically substitute demo records. Internal fixture/replay tools remain separate.
- Interrupted investigation: inspect its stored status. Never-started durable work may resume; claimed/uncertain work requires a fresh action/idempotency key. Reusing an old key returns its historical outcome.
- Deletion unavailable on an existing database: stop the app and follow the explicit initialization/recovery instructions in [the durable storage runbook](deploy/DURABLE_STORAGE.md). Do not bypass a missing established journal.
- Older status documents disagree: preserve their original evidence attribution and use current source, the linked recovery/deletion reports and this revision's verification boundary. Historical artifacts do not establish current release readiness.
