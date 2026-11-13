# Sueperman — SPEC.md (Codex implementation contract)

> **User override — 2026-11-13:** “System One” denotes the System 1 decision role for this implementation; the chosen provider is **OpenAI**. This supersedes every System One vendor/endpoint/key/model requirement below. Use OpenAI Responses API, server-only `OPENAI_API_KEY`, `OPENAI_ENABLED`, configurable `OPENAI_DECISION_MODEL` (default `gpt-6-luna`), strict four-choice structured output, sanitized state, `store:false`, no model tools, deterministic fallback and unchanged hard eligibility gates. Original 1.1 source text remains below for provenance; legacy vendor references do not control current orchestration. Sentry server/frontend project creation was separately approved and its local setup is documented in docs/sentry-setup.md.


**Version:** 1.1 (implementation decisions locked) · **Event:** AIE × MLH Hackathon @ Code Summit · **Date:** 2026-11-13 · **Owner:** Hackathon team

> **Copy into Codex:** “Implement Sueperman per this SPEC.md in the current repository. Follow the locked choices in §0; treat P0 as the non-negotiable goal and use fixture mode first. Implement in vertical slices, run tests at every checkpoint, then add *working* integrations in priority order. Do not pause for architectural preferences—choose the defaults below. No real claim submissions, fabricated facts, secrets in source, or unverified success claims.”

**Mission:** Build a consumer-remedy agent that ingests receipts/purchase records, autonomously finds matching **official product recalls** and **verified, open class-action settlements**, assesses documented eligibility, compiles source-cited claim packets, and requests explicit user approval before any action. It must complete a **realistic, auditable end-to-end workflow** within a hackathon day; it is not a legal-advice engine, legal-claim generator, or automated court filing system.

**Winner demo:** Upload 5 demo purchases → Gemini extracts product identifiers → official CPSC API finds an exact recall → Bright Data investigates an official manufacturer remedy page → a decision model routes ambiguous candidates → deterministic verifier rejects a near-match → UI displays linked evidence and a prepared refund/replacement request. Optional second branch: one *verified open* settlement with a correct deadline and administrator link; otherwise show a clearly labeled simulated settlement fixture.

**Deadlines:** Luma lists doors 9 AM, opening 10 AM or 11 AM in conflicting schedules, submissions **3 PM** (other third-party listings claim 5 PM). Design for the conservative **3 PM cutoff**, stop features by 2:20 PM, test/record by 2:40 PM, submit by 3 PM. Confirm final deadline with organizers onsite. Never delay a working submission to chase optional prizes.

**Non-negotiable:** One fully working recall flow beats 10 shallow integrations. **P0 runs offline using recorded fixtures with no paid keys.** Live integrations enhance it. Every external fact carries a retrievable URL, observed-at timestamp, and source type. No fabricated payouts, deadline, eligibility or submissions.

## 0. LOCKED IMPLEMENTATION DECISIONS — READ THIS FIRST

This section resolves competing options in the original plan. **Codex: implement these exact defaults, do not ask which approach to choose.** If an existing repo already works, adapt paths without changing behavior.

| Decision | Selection | Don't choose |
|---|---|---|
| Name | **Sueperman** (package name \`sueperman\`; UI “Sueperman — Your consumer-rights agent”) | Any legacy name |
| Languages | Python 3.12 backend; TypeScript Next.js frontend | Java, Go, mixed stacks |
| API | FastAPI, Pydantic v2, HTTPX | Express backend, GraphQL |
| State machine | Python typed stages and persistent AuditEvent rows | LangGraph, autonomous recursive agents |
| Storage | SQLite + SQLAlchemy 2, local uploads outside webroot | MongoDB, vector database, auth service |
| UI | Next.js App Router + Tailwind + native fetch and polling | Electron, Chrome extension |
| Packaging | uv for Python, pnpm for Node; Makefile root commands | handwritten dependency installers |
| Baseline model | no model required (CSV + rules); optional Gemini **2.5 Flash-Lite** for receipt extraction | LLM-based legal eligibility checks |
| Public recall authority | CPSC Recall API plus direct CPSC recall link | search snippets or generic news |
| Browsing | Bright Data MCP \`search_engine\`, then \`scrape_as_markdown\` | browser automation of claims |
| Decisions | System One \`decisions\` (validate in live model catalog); bounded 4-option Choice | free-form agent tool selection |
| Deployment | local app first, then DigitalOcean App Platform | deployment before tests |

### 0.1 Literal deterministic demo data

CSV fields: \`order_id,purchased_at,merchant,product_name,brand,model_number,upc\`. Create **exactly** these five synthetic rows, with any absent UPC represented by an empty field:

| ID | Purchased | Merchant | Name | Brand | Model | Expected |
|---|---|---|---|---|---|---|
| DEMO-001 | 2024-06-12 | Amazon | Portable Power Bank | NEWDERY | ZHX-PB22 | recall verified candidate, official CPSC 26-792 |
| DEMO-002 | 2024-06-13 | Amazon | Portable Power Bank | NEWDERY | ZHX-PB23 | rejected near-match |
| DEMO-003 | 2025-07-18 | Demo Store | Stainless Bottle | DemoCo | DC-BOTTLE-1 | no recall |
| DEMO-004 | 2024-06-14 | Amazon | Portable Power Bank | NEWDERY | *(blank)* | needs review / missing model |
| DEMO-005 | 2025-05-10 | Demo Store | Example Earbuds | DemoCo | DC-EARBUDS-1 | simulated settlement ONLY |

Recall fixture must be a **recorded copy of official CPSC notice 26-792** with \`official_url\`, \`fetched_at\`, \`source_type:government\` and model \`ZHX-PB22\`. Snapshot is labeled **OFFLINE REPLAY of a real published recall**; not “live verified now.” The fictional settlement is source_type \`fixture\` and always prominently simulated.

### 0.2 Matching code: implement as rules, not prompts

\`normalize_model(s)\`: Unicode NFKC → trim → uppercase → remove whitespace ONLY; retain \`-\`, digits, suffix letters and all other printable differentiators. Compare exact normalized model strings for a source record with explicit list of models. Example: \`ZHX-PB22\` matches \`zhx-pb22\`, but **does not** match \`ZHX-PB23\`, \`ZHX-PB22A\`, or \`ZHXPB22\` unless an official alias explicitly allows it. No substring or Levenshtein eligibility.

\`match_recall(product,recall)\` returns \`MatchResult(status,conditions,reasons,evidence_ids)\`:

1. Verify official source URL and affected brand/family.

2. If official model list is explicit: exact included model → continue; explicit different model → \`rejected\`; model absent → \`needs_review\`.

3. For every applicable batch/serial/date/region condition: false → \`rejected\`; unknown → \`needs_review\`.

4. Only if **all required conditions true** → \`verified_match\` (UI label “Recall matched — review details”).

5. If source missing/contradictory/untrusted → \`needs_review\` or \`unavailable\`, never \`verified_match\`.

For settlement use separate \`match_settlement\` with purchase time within class period inclusive, exact qualifying product, valid open deadline, proof requirements; outcome \`eligible_candidate\`, \`ineligible\`, or \`uncertain\`. Model scores cannot override these gates.

### 0.3 Precise provider sequence

- **P0:** \`FixtureReceiptExtractor\` (CSV) → \`FixtureRecallSource\` → hard-match → compose Markdown claim packet → persist event log → UI; complete with *no* API keys.

- **P1 Recall:** \`CPSCRecallSource\` queries official REST JSON first, then \`BrightDataResearcher\` obtains official manufacturer refund instructions using search/extract; source verification is deterministic and evidence-backed.

- **P1 Image:** \`GeminiReceiptExtractor\`: use \`google-genai\`, response JSON schema of \`{merchant?:string, purchased_at?:date, items:[{product_name:string,brand?:string,model_number?:string,upc?:string}]}\`; reject malformed and unverifiable identifiers. Images and PDFs cannot contain agent instructions.

- **P1 Decision:** System One POST \`https://system-one.dev/v1/systemone\` with \`model\` copied from GET \`/v1/models\`, \`state\` a **sanitized structured summary**, and \`questions.route={type:"choice",instructions:"Choose the safest next allowed investigation step",criteria:{inspect_more:"Need more official sources",request_user_info:"Missing identifier",produce_packet:"Verified hard-gates passed",reject_candidate:"Official evidence excludes product"}}\`. Parse \`answers.route.choice\`; reject unknown choice or malformed response and fall back to deterministic router.

- **P1 Settlement:** deterministic fixture evaluator is allowed immediately; live claims require administrator/court cross-verification before showing as real. Never scrape a logged-in or personalized claims portal.

### 0.4 UI labels and behavior, exactly

Primary nav: **Sueperman**, **My purchases**, **Opportunities**, **Activity**. Hero: “Find recalls and settlements hiding in your purchase history.” Primary CTA: **Check my purchases**; secondary **Try demo data**. While processing, show stage-by-stage audit timeline. Opportunity chips: **Recall matched**, **Needs information**, **Not affected**, **Simulated settlement**. Claim action: **Prepare claim packet** → **Approve draft locally** → **Export**. Never use “File claim” / “Claim submitted” or show payout balances. Each decision detail shows purchase-vs-official model comparison and linked evidence. Badges must identify fixture vs live data on every demo card.

### 0.5 Exact 90-second judge demo

0–10s: Open Sueperman and say “Your old purchases can qualify for refunds or recalls you never hear about.”
10–20s: Click **Try demo data**, show five rows, click **Check my purchases**.
20–45s: Open official NEWDERY recall match; show **ZHX-PB22**, CPSC source, hazard and full-refund remedy.
45–60s: Open **ZHX-PB23** negative case → model-mismatch rejection; show model hard-gates.
60–75s: Show manufacturer instructions from Bright Data if live, otherwise clearly labeled recorded data. Open claim packet, verify checklist, **Approve draft locally** and export.
75–85s: Show the synthetic settlement branch with SIMULATION banner.
85–90s: Display logs/provider modes; close with “One purchase history. Real evidence. Claims prepared, never fabricated.”

### 0.6 Stop conditions / trade-offs

Freeze features when **40 minutes remain before confirmed submission deadline**. Preserve a working commit and record backup demo. If CPSC live unavailable, use labeled fixture; if Bright Data/Gemini/System One unavailable, do not block. If exact recall matching and safe packets fail, do not implement Tiger Data/Snowflake. If time is limited, **drop all P2**, then live settlement, then optional AI models, in that order; never drop tests for false-positive rejection or source citations.

### 0.7 Definition of actually ready

On a clean clone with no API keys, \`make setup && make dev\` boots both apps; \`make demo\` yields expected 5-product results; \`make test && make smoke\` pass; Playwright checks exact match, excluded near-match, missing model, simulated settlement, and approved-local export; **no external submissions**. Update \`docs/SPONSORS.md\` to mark categories **PROVEN**, **PARTIAL**, **NOT IMPLEMENTED**, with evidence. Print counts and actual URLs, not claims of success without observed output.

---

## 1. Scope, milestones, exclusions

| Tier | Required functionality | Exit gate |
|---|---|---|
| **P0 (ship)** | Receipt/CSV upload; typed products; CPSC recall search; normalized candidate generation; exact model-number verification; evidence panel; safe remedy packet; reject near-matches; replayable demo fixtures; frontend/API; tests | Complete happy path + false-positive path in browser |
| **P1 (after P0)** | Gemini PDF/image receipt extraction; Bright Data web research; System One decision routing; deployed live URL; Sentry traces; real open settlement workflow with citation validation | Each integration actually invoked in a recorded run |
| **P2 (stretch)** | HyperFrames demo video; software-factory audit; Tiger Data event-series query/aggregate; Snowflake Cortex analysis; scheduled refresh | Only if P0/P1 are green and submission secured |

**Must not build:** user account system, Chrome extension, email account sync, payment authorization, real class-action submissions, refunds processing, authenticated scraping, auto-filing to legal administrators, long-running background scheduler, social login, legal advice chatbot, arbitrary RAG across the web, or a speculative “possible payout” total. A settlement requiring a membership, custom verification, sworn declaration, signature, SSN or identity document is preparation-only.

**Personas:** (a) consumer with order history, (b) judge viewing a seeded demo, (c) operator checking evidence quality.

**Core user story:** As a consumer, I upload proof of purchases so the agent can identify genuine remedies, explain why an item qualifies or not, collect missing evidence, and prepare a draft for my approval.

**Quality metrics:** false-positive rate on curated fixture corpus = 0; every positive recall requires exact relevant identifier and authoritative source; source coverage = 100% for material claim assertions; zero actual external submissions; one-command demo replay succeeds; each failing tool visibly degrades rather than crashing.

## 2. Architecture and stack

Use a simple **modular monolith**, not microservices.

**Frontend (locked):** Next.js App Router + TypeScript + Tailwind CSS + `pnpm`. Use native `fetch`, no Redux/GraphQL or component framework dependency. Browser pages: `/` upload/start, `/runs/[id]` timeline, `/opportunities/[id]` evidence/detail, `/claims/[id]` review/export. Display a persistent LIVE/REPLAY banner. React state + 800-ms polling of the run endpoint; accessible native controls.

**API/agent (locked):** Python **3.12** with `uv`, FastAPI, Pydantic v2, `pydantic-settings`, HTTPX, SQLAlchemy 2.x, Uvicorn; pytest + pytest-asyncio + respx for tests. Agent orchestration is a typed Python async state machine (no LangGraph or multi-agent framework). `BackgroundTasks` executes bounded runs in the API process, persisted as AgentRun; restarting may interrupt a run, which UI must report.

**Database (locked):** **SQLite** (`sqlite:///./sueperman.db`) for P0 with SQLAlchemy 2.x, schema created via `Base.metadata.create_all()` on startup in demo mode; WAL and foreign keys enabled. Postgres/Tiger Data is a separate P2 repository adapter; do not initialize it by default. Use UTC timestamps, UUIDs, unique idempotency keys, and indexed lookup columns. Never choose PostgreSQL merely because it is available.

- **Agent adapters:** ReceiptExtractor (Fixture/Gemini), RecallSource (Fixture/CPSC REST), WebResearcher (Fixture/BrightData), DecisionRouter (Rules/SystemOne), SettlementSource (Fixture/VerifiedPublicSources), ClaimComposer (deterministic template + optional Gemini). Every adapter declares provider/mode; errors are typed.

**Deployment (locked):** A working local app on `http://localhost:3000` and API at `http://localhost:8000` are first priority. Once green, deploy API via DigitalOcean App Platform using a Dockerfile; deploy Next.js as a second App Platform component if time allows. Put `/api/health` behind public routing and verify deployment with a real HTTP request. If DigitalOcean credentials are missing, demo locally and explicitly record the blocked sponsor category.

- **Operational:** Sentry optional; structured JSON audit events; opt-in provider flags; strict timeouts. Use typed dataclasses/Pydantic schemas between modules.

**Repository layout (use exactly unless an existing repo already provides an equivalent):**

~~~
sueperman/
  apps/web/                       # Next.js App Router + TS + Tailwind
    app/page.tsx
    app/runs/[id]/page.tsx
    app/opportunities/[id]/page.tsx
    app/claims/[id]/page.tsx
    lib/api.ts
  services/api/
    pyproject.toml
    app/main.py
    app/config.py
    app/db.py
    app/models.py
    app/schemas.py
    app/api/{uploads,runs,opportunities,claims,health,demo}.py
    app/agent/{orchestrator,states}.py
    app/matching/{normalize,recall,settlement}.py
    app/providers/{receipt,gemini,cpsc,brightdata,systemone,settlement}.py
    app/claims/compose.py
    app/security/source_policy.py
    tests/{unit,integration,fixtures}/
  demo/{orders.csv,recall_fixture.json,settlement_fixture.json,expected.json}
  docs/{architecture.md,DEMO.md,SPONSORS.md,FACTORY_EVIDENCE.md,known-limitations.md,implementation-log.md}
  scripts/{seed_demo.py,smoke_test.sh}
  Makefile
  .env.example
  docker-compose.yml              # optional, only if deployment needs it
  README.md
  SPEC.md
~~~

If the existing repository has established conventions, reuse rather than rewriting. Keep implementation simple: no Kafka, Celery, Kubernetes, Redis, autonomous subagent spawning, or agent-to-agent messaging.

**Environment switches:**

~~~
DEMO_MODE=true
DATABASE_URL=sqlite:///./sueperman.db
CPSC_LIVE_ENABLED=false
SETTLEMENT_LIVE_ENABLED=false
GEMINI_ENABLED=false
BRIGHTDATA_ENABLED=false
SYSTEM_ONE_ENABLED=false
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash-lite
BRIGHTDATA_API_TOKEN=
SYSTEM_ONE_API_KEY=
SYSTEM_ONE_MODEL=decisions
SENTRY_DSN=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
FRONTEND_ORIGIN=http://localhost:3000
~~~

Never put secrets in frontend bundles, logs, example fixtures or source control. Validate configuration at startup and display a provider-health section.

## 3. Domain model and canonical data contracts

All entities have UUID IDs, created_at/updated_at UTC, demo/simulated flag where applicable. Prefer JSON fields for raw extraction with normalized typed columns for matching.

**Purchase**: id, merchant?, order_date?, receipt_file_id?, source_type [csv|pdf|image|demo], imported_at, currency?, order_reference_redacted?.

**Product**: id, purchase_id, brand?, name, model_number?, serial_prefix?, UPC?, SKU?, quantity, product_category?, date_purchased?, extraction_confidence [0..1], raw_text_excerpt, user_confirmed_identifiers:boolean.

**Opportunity**: id, product_id, kind [recall|settlement], source_id, title, recall_or_case_reference?, official_url, remedy_kind [refund|repair|replacement|credit|other|unknown], deadline_at?, status [candidate|needs_review|verified_match|rejected|expired|unavailable], matching_reasons[], contrary_evidence[], source_observed_at, simulated:boolean.

**SourceEvidence**: id, opportunity_id, url, domain, publisher, source_type [government|manufacturer|administrator|court|secondary|fixture], fetched_at, title, quoted_excerpt (short), content_sha256?, extracted_facts JSON, authoritative_for[]; never represent third-party summaries as official evidence.

**EligibilityAssessment**: id, opportunity_id, outcome [eligible_candidate|ineligible|uncertain], confidence, hard_conditions [{name, expected, observed, status, source_id}], missing_fields[], reasons[], performed_by [deterministic|system_one_assisted], decision_model?, decision_raw_summary?, evaluated_at. UI must say “potentially eligible” unless external program formally confirms eligibility.

**ClaimPacket**: id, opportunity_id, version, status [draft|needs_evidence|ready_for_review|approved_local|exported], contact_or_portal_url, instructions, completed_fields JSON, required_documents[], missing_documents[], user_declaration_required:boolean, safety_instructions?, generated_at, reviewed_at?, approved_at?; contains no fabricated identifiers/declarations.

**AgentRun**: id, mode [demo|live], status [queued|running|completed|partial|failed], started_at, completed_at?, error_code?, provider_modes JSON. **AuditEvent**: id, run_id, seq (monotonic per run), stage, action, outcome, entity_id?, timestamp, duration_ms?, provider, source_refs[], redacted_details.

**JSON response envelope** for agent workflow:

~~~
{
  "run_id": "uuid",
  "status": "completed",
  "provider_modes": {"receipt": "gemini", "recall": "cpsc", "research": "brightdata", "decision": "system_one"},
  "summary": {"products_scanned": 5, "candidates": 2, "verified_matches": 1, "rejected": 1, "prepared_packets": 1},
  "warnings": [],
  "opportunities": ["uuid"],
  "events_url": "/api/runs/uuid/events"
}
~~~

Use stable API representation and JSON schema validation; never let a model directly create database records without validation.

**DB tables:** purchases, products, opportunities, source_evidence, eligibility_assessments, claim_packets, agent_runs, audit_events. Index model_number, UPC, source URL and event (run_id,seq). Use an idempotency key for import/run triggers; prevent duplicate opportunities via (product_id, kind, canonical source identifier).

## 4. Deterministic recall workflow (P0)

**Input:** CSV with headers order_id, purchased_at, merchant, product_name, brand, model_number, upc (last two optional). Image/PDF input is P1 and must route to the same normalized Product schema.

**CPSC provider—specific implementation:** Base URL `https://www.saferproducts.gov/RestWebServices/Recall`; GET with `params={"ProductName": product_name_query, "format": "json"}` over HTTPX, timeout 8s, 1 retry for transient 5xx/429. First search by `ProductName=power bank` or normalized `NEWDERY` name; filter locally by brand and affected model. Parse official response into a typed `RecallRecord` with recall number, product name, description, hazards, remedy, official URL and affected identifiers. If CPSC endpoint schema differs, inspect the documented response and update the adapter test; do **not** guess keys. Cache raw response with fetched_at. Use the government record as source of truth; a manufacturer page only supplies additional remedy steps.

**Candidate search:** lowercase, unicode normalization, trim punctuation, brand aliases only if explicitly configured; generate query using brand/name/UPC/model. Deduplicate by CPSC recall ID. Cap candidates to top 10 per product and show any truncation.

**Verification hard gates:**

1. Source is verifiably CPSC (or official manufacturer release directly linked from CPSC).

2. Brand/product family matches, with no contradictory brand evidence.

3. If recall specifies affected model identifiers, require **exact canonical model match** against the affected list (preserve letter/digit distinctions, suffixes and ranges). Never use fuzzy LLM similarity as final proof. If uncertain, status = needs_review.

4. If the recall restricts serial numbers, production dates, UPC, batches, geography or purchase windows, check each known condition; missing information means needs_review, not verified_match.

5. Check for an explicit remedy; safety notices and disposal instructions must be retained verbatim where relevant or correctly summarized with source references.

6. A close-looking but different model is rejected when an explicit affected model list excludes it.

7. Confidence measures can rank **investigation priority** but cannot override hard gates.

**Exact real recall demo fixture (verified 2026-11-13):** CPSC **recall 26-792**, NEWDERY power banks, model **ZHX-PB22**, recall date **2026-09-24**, remedy **refund**, official source `https://www.cpsc.gov/Recalls/2026/NEWDERY-Power-Banks-Recalled-Due-to-Fire-and-Burn-Hazards-Risk-of-Serious-Injury-Sold-on-Amazon`. Demo purchase A: brand NEWDERY, model ZHX-PB22 → verified recall candidate. Demo purchase B: NEWDERY ZHX-PB23 → rejected under the model-specific recall (synthetic, near-match negative). Do **not** claim any user got a refund. Display official stop-use and disposal instructions without replacing them with made-up procedures.

**Output:** verified match/needs review/rejected with explicit reasons, official URLs, and timestamps; then claim packet with steps, evidence checklist, contact/portal link and safety notice.

**Fail-closed:** Any missing official evidence, ambiguous model range, conflicting sources, unsupported API response or failed verification → needs_review. No positive conclusion from search snippets alone.

## 5. Settlement workflow (P1)

**Goal:** Discover **already-existing**, open, verified consumer class-action settlement opportunities; never suggest starting litigation or invent a legal entitlement.

**Trusted discovery hierarchy:** (1) court documents or government notices where available, (2) independently identifiable settlement administrator site and official case/court data, (3) reputable secondary search for discovery only. Search engines and settlement aggregators are **lead sources only**, never final evidence. Allowlisted source type verification is required before presenting a real opportunity.

**Ingest:** administrator URL, case title, official case number if available, court/jurisdiction, claim deadline, class period, settlement class definition, product or transaction qualifiers, exclusions, proof requirements, payment method/amount only when official documentation supports it, approved claim URL and source observed-at.

**Eligibility:** deterministic rules compare purchase date, geography, merchant, relevant product, class definition, and exclusions. Missing requirements → uncertain; expired deadline → expired; disqualifying facts → ineligible. Show the actual authoritative passage for every material condition. Do not assert “guaranteed payout,” “approved claim,” or expected payment amounts.

**Special guardrails:** Never auto-click submission, accept settlement terms, sign a sworn declaration, create fake receipts, bypass CAPTCHA or identity verification, or fill data not given by the user. If the portal requires personalized access, stop and present a handoff link. Pre-fill only verified user-provided information in a draft; the user must review all statements and submit independently.

**Settlement branch—exact offline implementation:** Seed a clearly fictional settlement called `DEMO SETTLEMENT — Example Earbuds Warranty Class`, for synthetic company `DemoCo`, eligible product `DC-EARBUDS-1`, purchase window `2024-01-01` through `2025-12-31` inclusive, fictional claim deadline `2026-12-31`, and proof requirement `receipt`. UI label on every screen: **SIMULATED CASE — NO REAL CLAIM AVAILABLE**. Source type must be `fixture` with repository file path, never a fake official URL. Use it to show deterministic date/product eligibility and claim-packet preparation, but do not include it in real financial totals or pitch as a live lawsuit. Replace with a genuine open administrator-verified case only if checked and traceable.

## 6. Agent state machine and adapters

**Canonical run stages:** RECEIVED → PARSED → PRODUCT_NORMALIZED → CANDIDATES_FOUND → SOURCES_VERIFIED → ELIGIBILITY_EVALUATED → PACKET_PREPARED → AWAITING_USER_REVIEW → COMPLETED. Nonterminal side states: NEEDS_INFO, PARTIAL, ERROR. Declined/rejected opportunity = terminal REJECTED (not a run error). Persist state transitions as AuditEvent before displaying them.

**Algorithm:**

1. Import receipt/CSV and validate schema + file size. Generate Product records; show uncertain fields to user.

2. Query CPSC for each product. In P1 additionally discover settlement leads (bounded/timeboxed).

3. Gather and validate primary sources (CPSC and source-restricted manufacturer/settlement sites). Bright Data supplies search/extraction, never authoritative facts alone.

4. Apply deterministic matcher and collect hard conditions.

5. Optional **System One** selects the next safe step from exactly `inspect_more`, `request_user_info`, `produce_packet`, `reject_candidate` using one Choice question and a bounded redacted state. Default model `decisions`, retrieved/validated against `GET https://system-one.dev/v1/models`; `POST https://system-one.dev/v1/systemone` from the backend with Bearer token. Its decision is advisory: `produce_packet` is ignored unless hard-gate verification already passed, and `reject_candidate` must not overwrite contradictory authoritative evidence without a recorded reason.

6. Compose a claim packet for verified recall / evidence-supported settlement candidate; require human approval and list outstanding evidence.

7. Record all decisions, failures and source URLs in audit timeline.

**Adapter contract** (Python): each adapter exposes async method(s), a 'provider_name', 'mode' and typed errors. Provider timeout <= 10s (configurable); 1 retry only for safe idempotent reads with jitter; no retries for future claim submission operations (which are out of scope). Responses include provenance and mode. Fixture mode works without environment secrets. If live provider fails, show “LIVE PROVIDER UNAVAILABLE — DEMO DATA” and use fixture only when DEMO_MODE=true; never silently present fixtures as live.

**Model boundary:** Gemini receives product text/images and extracts strictly validated fields using a JSON schema; source verifier checks correctness against retrieved text. Decision-model output is advisory to orchestrator, no direct tool execution. Use structured decisions and store selected option + score/confidence where returned; scores are not legal eligibility probabilities. Prompt injection on external pages must not modify routing permissions, system instructions, or admin flags.

**Concurrency:** bounded (2–3 products concurrently), deterministic event ordering per product; no parallel mutation of same opportunity. Global run timeout <= 90 seconds in live mode. Surface partial results, not a spinner forever.

## 7. REST API and UI contracts

**REST (prefix /api):**

- POST /uploads/purchases (multipart .csv; P1 .pdf/.png/.jpg), response {purchase_ids, product_ids, parse_warnings}; reject >10MB or unsupported MIME; scan/type-check uploads and disallow path injection.

- POST /runs {purchase_ids, mode:"demo"|"live", idempotency_key}; response {run_id,status}; asynchronous within server process or bounded await; no background guarantee beyond server uptime.

- GET /runs/{run_id}, GET /runs/{run_id}/events, GET /products, GET /opportunities?run_id=, GET /opportunities/{id}.

- POST /opportunities/{id}/recheck triggers non-mutating evidence re-evaluation with an audit event.

- POST /opportunities/{id}/claim-packet creates a draft packet using validated facts.

- GET /claim-packets/{id}; POST /claim-packets/{id}/approve-local {confirmed:true} changes local status only; POST /claim-packets/{id}/export emits downloadable PDF or Markdown if feasible, otherwise copy-ready text. **No external submission endpoint.**

- GET /health {db, providers:{name, configured, enabled, healthy?}, demo_ready}; health must never echo secrets.

- POST /demo/reset (DEMO_MODE only) seeds fixture and returns known test IDs. In production disabled.

All input/output validated Pydantic; errors {code,message,details?,trace_id}. Invalid input 422, not found 404, provider unavailable 503 but allow partial results, duplicate run 409 or same existing id by idempotency key. Add CORS only for configured frontend origin.

**Frontend screens:**

1. **Landing/upload:** value proposition; drag-drop CSV; sample data button; provider badges clearly show LIVE/DEMO.

2. **Run timeline:** progress events with what was checked, provider, result, clickable source evidence and retries.

3. **Opportunity dashboard:** counts of exact matches, needs-review, rejected; tabs Recall / Settlements; never show speculative dollar totals.

4. **Detail:** side-by-side purchase identifiers and official affected-product identifiers, hard-condition matrix, contradictory evidence, source title/URL/date; big safety notice for recalls.

5. **Claim review:** sourced remedy instructions, prefilled data (only known facts), required documents, missing information, clear “Approve draft” and “Export”; no “Submit claim” button.

6. **Demo-controls drawer:** Reset; Run deterministic demo; Run live APIs if configured; inject failure; toggle negative example.

**UX requirements:** good contrast, keyboard navigable controls, responsive desktop layout, loading/empty/error states, optimistic UI only for local operations, accessibility labels. Never claim an action happened until API confirms.

## 8. Sponsor prize strategy (genuine integrations only)

The project should **qualify based on demonstrated functionality**, not token mentions in a README. Each plugin has an integration test, actual call log or screenshots, and a one-line judge pitch in docs/SPONSORS.md.

| Category | Concrete role | Condition for claiming integration |
|---|---|---|
| Best Overall Hack | Real consumer problem + functioning end-to-end remedy workflow | exact recall demo + rejected near-match + safe prepared packet |
| Gemini API | Extract line items/model from image/PDF receipts (P1); structured output schema | screenshot/raw run evidence of real Gemini call and validated extracted JSON |
| Bright Data | Search and read public manufacturer/administrator pages via official MCP tools | real MCP request + source URL + extracted condition shown in UI |
| System One Models | Fixed-choice decision routing; choose investigate/ask/reject/packet | working API request using **catalog-validated** model ID; show returned choice and guardrail override |
| DigitalOcean | Host running web/API (App Platform or Droplet as appropriate) | public working deployment and health check |
| Sentry Raffle | Instrument backend errors and user flow with trace IDs | actual Sentry event / trace proof in dashboard |
| HyperFrames | Render a real 45–60s product demo from HTML storyboard | deliver generated demo video, not merely a storyboard |
| Cleanest Software Factory | Use Codex/Whirlwind or a transparent multi-step factory producing a tested component | show spec → generated code → tests → review/fix loop → final commit with artifacts |
| Tiger Data | Persist product/opportunity state transitions and timeseries run metrics in Tiger Data PostgreSQL; meaningful SQL aggregate/dashboard | live DB write and distinct query or continuous aggregate demonstrated |
| Snowflake | Import settlement-rule corpus; Cortex semantic/LLM analysis with source trace, verified by deterministic logic | actual Cortex query/agent result; Snowflake not required for P0 |

**Integration order (fixed):** (1) P0 offline, (2) CPSC live, (3) Bright Data, (4) Gemini, (5) System One, (6) Sentry, (7) DigitalOcean, (8) HyperFrames, (9) software-factory evidence, (10) Tiger Data, (11) Snowflake. Before each step re-run the offline smoke test. Spend max 10 minutes troubleshooting a sponsor login/key; if unavailable, mark `blocked` and move forward. No sponsor integration can sit in the mandatory happy path.

**Provider implementation specifics:** System One use `GET https://system-one.dev/v1/models` and `POST https://system-one.dev/v1/systemone` with `model:"decisions"`, `state` and one `questions.route` choice question; include a unique request idempotency key where supported, record output but never treat its probability as eligibility. **Bright Data:** connect through `@brightdata/mcp` via Python MCP stdio client and call exactly `search_engine` for discovery then `scrape_as_markdown` for a known official public page; enforce domain restrictions. **Gemini:** Python `google-genai`, default `gemini-2.5-flash-lite` if account supports it, JSON schema/Pydantic response for receipt lines, `temperature=0` where accepted; only use server-side. **Snowflake optional:** use current `AI_COMPLETE` not legacy `SNOWFLAKE.CORTEX.COMPLETE`; **Tiger Data optional:** write and query meaningful run-event time series, not a decorative connection.

## 9. Safety, security, and observability

**No legal or financial adjudication:** Product says it identifies opportunities, not legally guaranteed entitlement or approved refunds. For class actions do not assert eligibility when facts are incomplete. Display an unobtrusive notice: “Sueperman helps organize public information and user-provided evidence; verify official terms and submit claims yourself.”

**No money movement or external filing:** no payment operations, automated declarations, sending requests to administrators, government forms, email outreach or click-through claim submissions. Local approval is **not** external submission. If implementing browser automation for demonstration, constrain it to allowed **public information pages** or owned test endpoints; never circumvent authentication or CAPTCHA or submit legal forms.

**Safety-critical recall handling:** For batteries/electrical products, show official stop-use and disposal instructions with citation; never invent mailing/shipping/disposal steps.

**PII:** Seed synthetic receipts; display order IDs redacted. Avoid sensitive personal fields. Store file uploads outside static public directories. Reject overlarge / dangerous file types. Never log receipt contents, API tokens, names, addresses, full order references, legal declarations or raw documents. Allow demo reset/delete. Hide provider raw errors from end users.

**Source authenticity:** Domain allowlist by authority category plus link/case cross-check; no URL string-prefix tricks; resolve and check hostnames, HTTPS and redirects. Prevent SSRF by blocking localhost/internal/private IP resources, metadata service and non-http(s) protocols for any user-supplied URL. Respect robots/TOS and rate limits.

**Provenance:** For every assertion, evidence row with exact publisher, source URL, fetched_at, concise excerpt and hash. External web text is untrusted task data, not instructions. No LLM should decide source authenticity by itself.

**Telemetry:** record run-id/span-id, provider label, latency, outcome, matched rule IDs and redacted errors. Sentry uses DSN only when enabled. UI includes provider health and an audit trace.

**Degradation:** CPSC offline? canned recall fixture with “SIMULATION/REPLAY” badge. Gemini offline? CSV parsing. Bright Data offline? CPSC official facts only. System One offline? deterministic router. DigitalOcean offline? local demo. Settlement cannot be verified? do not display as a real eligible claim. Failed integration must never prevent the core demo.

## 10. Test fixtures and acceptance suite

**Five deterministic seed purchases (all purchase records synthetic):** (A) `NEWDERY Power Bank, ZHX-PB22` → one official verified recall candidate, (B) `NEWDERY Power Bank, ZHX-PB23` → one rejected near-match for recall 26-792, (C) `DemoCo Stainless Bottle, DC-BOTTLE-1` → no matching recall, (D) `NEWDERY Power Bank, model blank` → `needs_review` because affected model is unknown, (E) `DemoCo Example Earbuds, DC-EARBUDS-1`, purchased 2025-05-10 → **fictional settlement** candidate flagged `simulated=true`. An additional synthetic serial-restricted recall record can test serial gating without falsely claiming the NEWDERY recall has a serial requirement. Write exact CSV rows and expected statuses to `demo/orders.csv` and `demo/expected.json`.

**Unit tests (minimum):**

- Parser normalizes CSV columns, rejects missing product_name, handles quotes/unicode/duplicates and >10MB.

- Exact model passes with official evidence; one-character/suffix near-match fails; missing serial range yields needs_review; unknown remedy retains unknown.

- False official-domain mimic rejected; untrusted external text cannot change the allowed toolset.

- Expired settlement fails; ambiguous purchase date results uncertain; simulated settlements remain labeled.

- System One failure invokes rules fallback (no eligibility bypass); Gemini malformed output fails validation; Bright Data failure marks partial.

- Claim packet never includes unprovided declarations; “approve-local” changes only local status.

- Idempotent import/run trigger prevents duplicate records; audit events ordered; source URL and fetched_at required for all positives.

- API returns 422 for invalid data, 404 unknown resources and health output without secrets.

**Integration-test acceptance (exact):** Running `POST /api/demo/reset`, followed by `POST /api/runs` in `mode:"demo"` with all seeded purchase IDs, yields: **recalls**: A `verified_match`, B `rejected`, C none, D `needs_review`; **settlements**: E one prominently simulated candidate; **claim packets**: exactly one ready-for-review recall packet for A (settlement draft may be additional, but excluded from real-remedy count). Run IDs unique, idempotent resubmissions of the same idempotency key return the original run ID; no fake legal filing. Reset/run repeated twice yields the same facts and status counts.

**Browser E2E (required; Playwright):** Load `http://localhost:3000`; select `Load demo purchases`; verify five items; click `Run Sueperman`; poll to completed; verify exact NEWDERY recalled model is shown with citation; click it, read evidence, click `Prepare claim`, then `Approve draft locally`, then `Export Markdown`; verify export. Open near-match B and confirm `REJECTED — MODEL MISMATCH`. Open settlement E and verify `SIMULATED CASE`. Take screenshots of dashboard, evidence, claim packet and rejection. No ‘Claim submitted’ success text anywhere.

**Commands (must be implemented exactly in root Makefile):** `make setup` installs `uv`/Python dependencies and `pnpm`/Next.js dependencies (document prerequisites); `make dev` starts API on port 8000 and web on 3000, `make seed` seeds records, `make test` runs backend pytest + frontend/unit checks, `make demo` resets and triggers fixture run with its returned JSON summary, `make lint` runs Ruff + ESLint, `make typecheck` runs MyPy or Pydantic-model validation and `tsc --noEmit`, `make smoke` verifies both health and a seed-run. Commands must fail nonzero on error, not print fake success. README has copy/paste setup and troubleshooting.

**Definition of done:** local boot succeeds; deterministic demo completes twice; tests pass; no secret leakage; all source claims clickable; negative test visibly rejects; claim export is useful; at least one live sponsor API proves integration (if available); demo recording saved. Do not declare done with failing checks—document remaining gaps.

## 11. Execution sequence for Codex: autonomous but test-first

**Phase 0 (first 10 minutes):** Inspect repo and git status; preserve existing work; check `python3.12`, `uv`, Node 20+, `pnpm`, available ports, env variable *presence only* (never print secrets). Create the exact folder skeleton and `.env.example`. Write docs/implementation-log.md with checklist, constraints and 3 PM cutoff. If repo is empty, scaffold Next.js App Router and Python FastAPI only—do not create a deployment pipeline yet.

**Phase 1 (P0—ship this first):** 1) schemas+SQLite tables; 2) five-row CSV fixtures and official recall snapshot; 3) csv parser; 4) matcher exact model and missing-model gates; 5) FastAPI upload/demo/reset/run/detail/packet routes; 6) backend fixtures + 8 minimum tests; 7) Next.js upload/dashboard/detail/packet screens; 8) Playwright exact/near-match test. After each numbered step run targeted pytest or app smoke; at completion run `make test && make smoke` and record results. Do **not** spend P0 time on OAuth, PDF, payment, or integrations.

**Phase 2 (live evidence):** 1) CPSC API adapter (`GET /RestWebServices/Recall?ProductName=...&format=json`), real request smoke check; 2) government-record normalization, official citation and cache; 3) Bright Data MCP `search_engine`→`scrape_as_markdown` for official manufacturer refund page, record extracted facts and URL; 4) domain/redirect validation and source provenance tests. Keep fixture fallback clearly labeled. Phase exit: one successful live CPSC lookup and one successful Bright Data public-page extraction *if keys exist*, without changing P0 results.

**Phase 3 (AI and settlement):** 1) `google-genai` for photo/PDF extraction with typed JSON output (start with 1 PNG test fixture, then PDF if time); 2) System One `decisions` choice routing with a documented POST and validation; 3) simulated settlement rule evaluator and UI (already seeded), only then optional independently verified live open settlement; 4) prove a model cannot override hard gates in tests. Every remote model is wrapped behind a feature flag with deterministic fallback.

**Phase 4 (finish/demo/sponsors):** 1) Sentry error event plus sanitized audit trace; 2) deploy via DigitalOcean after `make smoke` passes locally; 3) record 90-second live demonstration + 45–60s HyperFrames video if time; 4) keep docs/SPONSORS.md honest with screenshots/IDs; 5) export a spec→code→tests→review→fix factory log if genuinely executed; 6) ONLY after submission is safe add Tiger Data event metrics and Snowflake `AI_COMPLETE`. Freeze features 40 minutes before official cutoff; commit/tag working version; upload submission by confirmed cutoff.

**Repository delivery artifacts:**

- Running app, complete source, SPEC.md, README.md and .env.example.

- docs/DEMO.md: 90-second script with exact clicks and expected screens.

- docs/SPONSORS.md: all 10 categories marked proven / partial / not implemented, with evidence URLs or local logs.

- docs/FACTORY_EVIDENCE.md: spec, prompts, generated component, tests, feedback, fixes, commits (only if actually produced).

- docs/architecture.md: state machine, provenance trust boundaries, provider adapter contracts, failure modes.

- docs/known-limitations.md: missing live credentials, non-covered settlements, legal boundaries, fixture vs live.

- scripts/smoke_test.sh and tests runnable in CI.

- demo assets / screenshots, and demo video if produced.

**Codex operating rules:** Make decisions using **§0 locked defaults**, not open-ended framework debates. Avoid clarification unless blocked by credentials or missing repo access. Implement smallest vertical slice first, run real checks and document failures. Commit in short checkpoints, do not overwrite existing work, and never imply any API was called if disabled. Keep docs/implementation-log.md as `TODO → DOING → PASS/BLOCKED` with timestamps and commands. Stop feature work before submission, provide real URLs/test counts and an honest sponsor matrix.

## 12. Key official references (verify at implementation time)

- Event and deadline (conservative 3 PM): https://luma.com/AIECodeSummitHackathon

- CPSC recall API guide: https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information

- CPSC REST recall endpoint docs: https://www.saferproducts.gov/RestWebServices/Recall

- Bright Data MCP reference: https://github.com/brightdata/brightdata-mcp

- Gemini Python SDK: https://googleapis.github.io/python-genai/

- System One model capabilities & catalog: https://docs.system-one.dev/en/docs/models

- System One homepage: https://system-one.dev/en/about

**Architecture decision record:**

- AD-01: offline-first deterministic P0 to guarantee an assessable demo.

- AD-02: eligibility from authoritative evidence + hard checks, never a pure model assertion.

- AD-03: external claim submission explicitly out of scope; approval only local.

- AD-04: every sponsor optional; disabled providers cannot crash the run.

- AD-05: settlements have higher provenance threshold than recall API matches.

- AD-06: track time; freeze core before submission, prioritize Best Overall.

**End of specification. Codex should begin Phase 0, then implement without further planning documents unless needed for blockers.**
