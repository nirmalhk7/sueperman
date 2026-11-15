# Sueperman V2 — Diwali Festiverse Agent-to-Agent Hackathon | Implementation SPEC

**Version:** 2.1 · **Event:** Diwali Festiverse Agent-to-Agent Hackathon, November 13–19, 2026 · **Status:** execution contract, not implementation evidence. Start with §13; §14 defines the acceptance harness. Predictability means stable behavior, bounded changes and verifiable completion—not identical generated source code or identical live model wording.

**Source-of-truth links:** [Original Sueperman SPEC.md](https://chatgpt.com/space/page_dc851727187081919b3e151fa9344be1) · [Existing public repository](https://github.com/nirmalhk7/sueperman) (default branch: **codex/sueperman** at review) · [Existing published demo](https://sueperman-6t4xk.ondigitalocean.app) · [Diwali event / rules](https://luma.com/bc8etq9q)

> **Codex operating directive:** Extend the existing repository on **codex/diwali-v2**, preserving V1 behavior. Implement only the selected gates in §14; the first invocation targets **G0–G3**, not the entire roadmap. Freeze the baseline and expected outcomes before implementation. Do not weaken a test, invent an API, substitute a sponsor or expand scope to bypass a blocker. Missing credentials block live proof, not independent offline work. Stop at the requested gate with the structured handoff. No real claims, wallet transactions, paid calls, pushes, publication or deployment without the applicable explicit authorization.

## 0. Fit assessment and competition contract

**Verdict: strong fit IF Sueperman V2 shows independent agents communicating and changing a consequential decision.** It is not enough to rebrand the original single-process research pipeline as “multi-agent.” The signature differentiator is a skeptic agent catching a plausible false-positive recall match, with evidence shared across agents and a deterministic rule engine enforcing the result.

**Primary official track:** **Research — Data & Build.** Research Agent collects and structures official recall/remedy evidence; Builder Agent turns that data into an interactive consumer case dashboard and usable remedy packet. Secondary narrative: consumer financial protection. **Do not claim to satisfy the Finance — Analyze & Trade track** merely because potential refunds have monetary value; that track specifically describes market analysis and simulated trades.

**Target:** one credible end-to-end product entering the best applicable use-case categories, with five genuine sponsor touchpoints when feasible: **BAND, Lyzr, Finch, Agent37, AdaL.** Sponsor count is NOT an official multiplier of judging score. Reliability and demonstrable collaboration take precedence over superficial logos.

**Event rules verified from the Luma listing:**

- Solo team or two people maximum.

- Submission: public source repository plus demo **no longer than 2 minutes** by **Wednesday, November 18, 2026, 6:00 PM Pacific**. Online preliminary judging November 18, 6–8 PM; finalists present November 19, 1–3 PM; winners announced November 19, 3–5 PM.

- Use AdaL to create a video showing the project for presentation; use the sponsor platforms genuinely for their respective prize considerations.

- **Eligibility is accepted for this build because the owner has stated Sueperman is eligible. Do not reopen this question or block implementation.** Record that statement accurately in docs/DIWALI_ELIGIBILITY.md, preserve the published rule and distinguish pre-existing code from event contributions. Do not invent an organizer name, approval message or exception.

**Submission cutoff strategy:** by November 18 at 3:30 PM Pacific freeze risky features; by 4:30 PM have a tagged working commit, public URL, screenshot/log evidence, and AdaL MP4; submit by 5:00 PM and keep one hour contingency. The authoritative cutoff remains 6:00 PM. No feature can consume the submission buffer.

**Non-negotiable winner scene:** five synthetic purchases → visible BAND delegation → researcher uses official CPSC notice → skeptic challenges a near-match → deterministic verifier rejects **NEWDERY ZHX-PB23** while matching **ZHX-PB22** for recall **26-792** → Builder produces a documented review/export packet → user approval remains local. At least one real Lyzr execution must contribute an auditable structured assessment. Optional Agent37/Finch deepen that same case. The sequence must be genuine, not scripted chat text.

## 1. Retain current system; do NOT rebuild

At review, the GitHub repository documents an existing Next.js/FastAPI/SQLite modular monolith with CPSC REST adapter, official NEWDERY recall match and one-character near-match rejection; uploaded CSV and image/PDF extraction adapters; optional Gemini/Bright Data/OpenAI models; a reviewed, constrained Kroger settlement branch; source evidence, audit events, claim-packet approval/export; Sentry and DigitalOcean integration; and existing automated unit/integration/browser checks. Treat these as **documented baseline capabilities**, NOT as proof that the latest branch or every remote provider is healthy today. Run fresh checks before assigning PASS.

**Locked stack:** Python 3.12, FastAPI, Pydantic v2, HTTPX, SQLAlchemy 2 + SQLite WAL; Next.js App Router + TypeScript + Tailwind + native fetch; uv + pnpm. Existing APIs remain backward compatible; add routes/tables/columns through additive migrations. Do not replace SQLite with PostgreSQL, add Kafka/Redis, move to microservices, or migrate the app to a sponsor's hosted stack.

**Unchanged safety authority:** existing exact recall eligibility/identifier checks, manufacturer/CPSC provenance checks, stale-evidence invalidation, explicit missing-data states and local-approval/export gates. Generative agents only research, challenge, explain, summarize, and propose the next safe action. They cannot independently mark eligible, authorize a refund, claim a payout, send a declaration, or submit to an external portal.

**Preserve these existing interfaces by adaptation, not duplication:** receipt parsing and imported Product rows; RecallSource/CPSC and Bright Data public research; match_recall and match_settlement; eligibility/SourceEvidence records; ClaimPacket composition and local approval; AgentRun and AuditEvent; existing run/dashboard/opportunity/claim frontend paths. Inspect exact current identifiers before editing: file paths here are proposed where not already present.

**Branch safety:** G0 records HEAD, branch, dirty paths and dependency-lock digests. Resume codex/diwali-v2 if it exists. Otherwise branch from the verified working HEAD only when doing so will not disturb user changes. Never reset, stash, stage, commit or overwrite unrelated work. A conflicting dirty worktree is BLOCKED, not permission to choose another base. No existing dependency upgrades or V1 refactors for a sponsor. Record local checkpoint commits only for task-owned changes when permitted; remote writes remain separately authorized.

## 2. Locked V2 architecture — the minimum genuine A2A system

**Locked topology:** one FastAPI deployment, one Uvicorn worker and exactly four logical actors with separate identities, inboxes and handlers. The coordinator is the only V2 workflow/database writer; actors receive immutable input and return validated data, never SQLAlchemy sessions. BAND mode uses four distinct authenticated identities. Local-test transport invokes the same handlers and reducer without network access. Do not add microservices, another orchestrator, an agent framework, a database broker or autonomous agent spawning. Lyzr provides one reviewer; Finch supplies its pinned procedural skill; Agent37 optionally executes bounded public research; AdaL produces the presentation.

**Agents with independent identities, bounded authority and separate tasks:**

| Role key | Responsibility | Allowed work | Prohibited |
|---|---|---|---|
| manager | Own reducer, scheduling and finalization | Persist validated results through compatibility facade; enforce budgets and policy | Invent evidence or bypass matcher |
| researcher | Return candidates and requested public facts | Existing CPSC adapter; one public-source follow-up; optional Agent37 worker | Decide eligibility, write database, access private portals |
| skeptic | Independently check purchase against evidence | Existing pure matcher; one Lyzr reviewer; pinned Finch skill in review context | Override hard conditions or approve a packet |
| builder | Return typed case view and unsigned draft | Existing pure composer and fixed rendering templates | Generate executable UI code, write database, approve, export or submit |

Receipt intake remains V1 functionality; there is no fifth actor. Human approval remains an explicit user action. Four actors does not mean four LLMs: manager and builder are deterministic, researcher performs bounded tool work, and skeptic uses Lyzr for evidence questions while deterministic rules govern eligibility.

**A2A proof:** exactly four actor identities and four distinct BAND identities for live proof. A positive case traverses manager → researcher → manager → skeptic → manager → builder → manager. Capture receipt and consumption, not just successful sending. A negative case stops before builder. Local transport is labeled LOCAL TEST and cannot count as BAND usage. The review tests a candidate—not a deliberately fabricated positive decision—and does not claim improved accuracy over the existing correct matcher without measured evidence.

**Canonical message contract (Pydantic and JSON schema):**

```json
{
  "schema_version": 1,
  "message_id": "11111111-1111-4111-8111-111111111111",
  "run_id": "22222222-2222-4222-8222-222222222222",
  "case_id": "33333333-3333-4333-8333-333333333333",
  "task_id": "44444444-4444-4444-8444-444444444444",
  "correlation_id": "33333333-3333-4333-8333-333333333333",
  "causation_id": "55555555-5555-4555-8555-555555555555",
  "expected_case_revision": 1,
  "sender": "researcher",
  "recipient": "manager",
  "type": "ResearchReport",
  "sent_at": "2026-11-15T00:00:00Z",
  "deadline_at": "2026-11-15T00:00:10Z",
  "source_refs": ["cpsc:26-792:snapshot-1"],
  "payload": {
    "candidate_refs": ["cpsc:26-792:snapshot-1"],
    "coverage": "supported_scope",
    "truncated": false
  }
}
```

These are illustrative IDs. Inject ID generation and clocks in tests. Envelope and typed payloads reject extra fields; timestamps require timezones; payload limit is 16 KiB UTF-8. Resolve source references only against immutable run-scoped snapshots. Trusted adapters record actual transport/provider mode; messages cannot self-declare LIVE. Compare the authenticated platform sender and recipient with the actor registry.

**Closed wire types:** ResearchRequested, ResearchReport, ReviewRequested, ReviewReport, FollowUpRequested, FollowUpReport, BuildRequested, BuildReport, TaskFailed. Sender/recipient and payload rules are in §14. **Separate audit events:** ChallengeRaised, EvidenceAdded, CaseFinalized, PacketPrepared, HumanApprovalRequested, RunPartial, RunFailed and RunCompleted. A validated ReviewReport can cause ChallengeRaised; audit-event names are not extra wire types. Never manufacture a transcript to satisfy the presentation.

**Conversation protocol:**

1. Manager freezes purchase/configuration inputs, creates one case per demo product and sends ResearchRequested. Process the five fixture products in input order, with at most one active case.

2. Researcher returns normalized candidates and source facts to manager. Coordinator validates and stores immutable evidence snapshots before ReviewRequested. Researcher never writes SourceEvidence. Candidate relevance is not eligibility.

3. Skeptic invokes the existing pure matcher independently. Lyzr may supply evidence questions, not a new match status. ReviewReport includes the deterministic result, compared identifiers and supported challenge code. Manager rechecks the authoritative result before finalization.

4. Explicit trusted model exclusion emits ChallengeRaised and finalizes REJECTED immediately, without a debate or builder task. Missing purchase identifiers finalize NEEDS_REVIEW with one user question; a web agent cannot supply private purchase facts. Only a missing public-source fact permits one FollowUpRequested → FollowUpReport → second review. Remaining uncertainty stays NEEDS_REVIEW.

5. Only a verified recall with current evidence permits BuildRequested. Rejected, unknown, no-match and simulated-settlement cases never enter the real-recall builder. No-match means no result within supported searched scope—not proof that the product is universally safe.

6. Builder returns an unsigned draft and typed case-view data using the existing pure composer. The coordinator checks purchase/evidence digests again before saving. No generated HTML/JavaScript execution, approval, export or remote filing occurs in this stage.

7. Coordinator finalizes through the transaction boundary in §14. UI renders only persisted accepted events. Existing user approval/export routes retain responsibility for explicit confirmation and stale-evidence checks. Actors never invoke those routes.

8. Transport failure, deadline or process restart cancels outstanding work and closes the run as partial or failed. Do not change a BAND run into local transport. A user-requested deterministic fallback is a new run with a new idempotency key and fallback_of reference. Never substitute demo records for real private input.

**Skeptic independence test:** Researcher must not send “verified_match” as a conclusion the Skeptic blindly repeats. The Skeptic must receive raw structured official identifiers/source references, compare them with a distinct local verifier invocation, and report an explicit rule result. The opposite outcome for PB22 vs PB23 is the judge-proof behavior.

## 3. Sponsor integration contracts — build all five without coupling the demo to all five

| Sponsor | Locked responsibility | Gate and proof |
|---|---|---|
| BAND | Transport for four actor identities | G4: real send, receipt and consumption within the case |
| Lyzr | One Skeptic evidence-review agent | G5: real inference, schema-valid response and observable use |
| Finch | Pinned Recall Evidence Auditor skill in reviewer context | G6: listing/version/package digest plus an invocation that loaded it |
| Agent37 | Execute the bounded public-evidence worker | G7: owned sandbox, task/result, local verification and confirmed cleanup |
| AdaL | Edit actual recordings into the submission video | G8/G9: footage manifest, AdaL export evidence and playable MP4 under 120 seconds |

**BAND:** wrap actor handlers in the documented custom Python adapter; do not adopt another agent framework. The [SDK reference](https://docs.band.ai/reference/sdk) currently documents band-sdk 8.1.0. G4 must verify Python 3.12 compatibility, pin one working release and record its exact adapter, lifecycle, sender-authentication and message interfaces in the provider lock. Use the matching [custom-adapter reference](https://docs.band.ai/advanced/creating-adapters), not mixed-version examples. Prove a minimal round trip before application wiring. Two failed, documented compatibility hypotheses end the spike as BLOCKED; do not change languages or architecture.

**Lyzr:** exactly one configured reviewer. The [Chat API](https://docs.lyzr.ai/enterprise/api/agents/chat) documents `POST https://agent-prod.studio.lyzr.ai/v3/inference/chat/`, header `x-api-key`, and fields `user_id`, `agent_id`, `session_id`, `message`; the response example contains a `response` string. Use this documented interface, not the earlier speculative agent-ID chat path. Use an application identity and a run/case/role-specific session. Validate a JSON object inside the response against the application-owned review schema: review_note, requested_fields, evidence_refs, uncertainty. Requested fields are limited to affected_models, remedy_instructions, proof_requirements and safety_instructions, maximum two. No status, payout, invented identifier, arbitrary URL or tool instruction is accepted. No POST retry or model-based JSON repair; malformed output is an explicit provider failure.

**Finch:** produce one package, `sueperman-recall-evidence-auditor`, containing SKILL.md, existing rule references and synthetic examples. It supplies procedures, never executable authority or a replacement matcher. Pin exact bytes and SHA-256. After authorized publication, load the package retrieved from its recorded Finch listing/version into reviewer context and record the loaded digest and invocation. A local file alone is not Finch proof. No unrelated skill purchase, guessed execution API or new runtime. Wallet/signing/publication require owner action; unavailable access blocks sponsor proof while local skill tests continue. Reject archive traversal, executable hooks and secrets. Reference: [Finch skill publication](https://www.finchtech.ai/en/story/publish-skills).

**Agent37:** one prewarmed, owned sandbox executes bounded public research; do not migrate the application. The [Cloud documentation](https://www.agent37.com/cloud) demonstrates instance creation at `/v1/instances`; G7 must additionally verify exact execution, result-read and deletion operations before integration. Missing contracts mean BLOCKED, not invented endpoints. Send synthetic attributes and approved official URLs only; verify returned facts locally. Provisioning timeout has an unknown outcome: reconcile owned resources before retrying. Confirm deletion, because disk can remain billable while compute is stopped. Application-side request/time caps are not guaranteed provider billing caps. No automatic top-up, card attachment or paid provisioning.

**AdaL implementation:** use AdaL's video producer to assemble REAL screen recordings of the agent collaboration, evidence diff, packet export, and source citations into a narrated, captioned **16:9 MP4 under 120 seconds**. Keep original and edited footage, AdaL project metadata and render verification. No invented screenshots, scripted “live” A2A exchanges or generated results. AdaL currently documents macOS 15+ for saving MP4 on Mac; verify OS compatibility early. Docs: https://docs.sylph.ai/features/video-producer/ and https://adalagent.ai.

**Two separate scoreboards:** implementation gates use NOT_STARTED, PASS, FAIL or BLOCKED. Sponsor proof uses NOT_STARTED, IMPLEMENTED_UNVERIFIED, PARTIAL or PROVEN. A passing mocked adapter test is not sponsor proof; a missing key is not a code failure. Every PROVEN row must identify the actual invocation/export, source run, tested commit/configuration, observed timestamp and evidence artifact. A report generator derives statuses from verified artifacts, never prose assertions. Stale evidence stays labeled with its original commit and does not prove a changed adapter.

**Build order:** G0 baseline → G1 oracle/contracts → G2 local actor flow → G3 persistence/API/UI → G4 BAND → G5 Lyzr → G6 Finch → G7 Agent37 → G8 release assets → G9 live/submission audit. Check AdaL availability early without creating a video before real footage exists. Each provider spike permits one documented primary integration path and one repair; otherwise mark the precise blocker and preserve working gates. Do not silently introduce alternative providers.

## 4. Reuse exact consumer cases from V1

Keep the five synthetic purchases and preserve the outcomes:

| Synthetic purchase | Expected result | Required proof |
|---|---|---|
| DEMO-001 NEWDERY power bank **ZHX-PB22** | Official recall **26-792** matched; safety notice and packet after review | CPSC official notice URL, exact model, evidence matrix, local export |
| DEMO-002 NEWDERY power bank **ZHX-PB23** | **REJECTED** near-match | Side-by-side PB23 vs PB22, explicit Skeptic ChallengeRaised, no positive packet |
| DEMO-003 DemoCo stainless bottle **DC-BOTTLE-1** | No verified recall | No fabricated opportunity |
| DEMO-004 NEWDERY power bank with unknown model | **NEEDS REVIEW** | Agent asks for model instead of guessing; no verified match |
| DEMO-005 DemoCo earbuds **DC-EARBUDS-1** | Fictional settlement fixture only | Persistent “SIMULATED CASE — NO REAL CLAIM” label; no official URL or payout |

**Official CPSC reference:** https://www.cpsc.gov/Recalls/2026/NEWDERY-Power-Banks-Recalled-Due-to-Fire-and-Burn-Hazards-Risk-of-Serious-Injury-Sold-on-Amazon. Show official stop-use/handling/disposal/refund instructions in source-cited form, never improvise battery disposal/shipping instructions. The model number comparison must preserve dashes, suffixes, digits and exact affected-model scope.

**Optional but valuable:** a source-reviewed live settlement case already exists in V1. It can support the consumer-impact narrative but should NOT become the Diwali hero path. Never claim a consumer is legally eligible unless all class conditions are documented. Real settlements stay preparation-only; no filing, signatures, payment promises or claimed refund totals.

## 5. New persistence, API and UI — additive only

**Proposed files, adjust to real repo paths rather than duplicate established modules:**

~~~
services/api/app/diwali/
  coordinator.py
  message_schema.py
  band_bridge.py
  agent_registry.py
  research_worker.py
  skeptic_worker.py
  builder_worker.py
  provider_lyzr.py
  provider_agent37.py
  finch_skill.py
  policy_gate.py
  replay.py
  tracing.py
services/api/tests/diwali/
  test_messages.py
  test_band_bridge.py
  test_lyzr_contract.py
  test_finch_skill.py
  test_agent37_contract.py
  test_skeptic_policy.py
  test_failures.py
apps/web/
  (reuse existing run/opportunity screens)
  components/diwali-agent-timeline.tsx
  components/diwali-case-evidence.tsx
skills/sueperman-recall-evidence-auditor/
  SKILL.md
  references/recall-policy.md
  fixtures/expected.json
docs/
  DIWALI_ELIGIBILITY.md
  DIWALI_IMPLEMENTATION_LOG.md
  DIWALI_SPONSORS.md
  DIWALI_DEMO.md
  DIWALI_ARCHITECTURE.md
  DIWALI_LIMITATIONS.md
  evidence/diwali/
~~~

**Additive persistence:** add diwali_cases (run/product, phase, revision, frozen purchase/evidence, hashes, final references), agent_messages (unique message ID, task/case/run, accepted sequence, transport metadata, delivery state, redacted envelope), agent_tasks (unique logical task, role, deadline, state, attempts) and provider_invocations (task/provider, configured version, mode, observed ID, latency, evidence digest). Keep AgentRun/AuditEvent and existing domain tables. Use explicit additive setup with a version marker and schema checks; no dropped/rebuilt legacy tables. Runtime imports must not silently mutate a production database. Coordinator-only writes and rollback/crash rules are specified in §14.

**Additive REST:**

- **GET /api/runs/{run_id}/agent-messages?after_seq=0&limit=100** returns `{items,next_seq}` ordered by server-assigned accepted sequence, not provider timestamps. Limit range 1–100. Existing V1 runs return an empty list; unknown runs return 404. Only sanitized accepted envelopes are exposed.

- **GET /api/integrations/diwali/status** returns configured/enabled plus cached last observation and timestamp. A GET never invokes a paid provider. An environment variable means configured, not healthy or proven. Unobserved health is null.

- Extend the existing run request with **collaboration_mode: deterministic | local | band**, default deterministic, and optional fallback_of. Preserve existing `mode: demo | live`; source mode and transport are independent. Omitted new fields retain V1 semantics. Local mode requires demo data and blocks network. BAND mode requires an operator-authorized run over the pinned synthetic dataset, verified identity configuration and available transport. Check capability before creating work: disabled feature 403; missing configuration 503; invalid input 422. No quiet mode substitution.

- **POST /api/demo/diwali/reset** is local/operator-only, uses an isolated demo database, and returns 409 while a run is active. It reuses the original five-row seed and must not delete private or unrelated records. Keep it disabled on an unattended shared public service.

- Existing opportunities, local approval and export APIs remain unchanged. Do not add a submission endpoint.

**UI contract:** preserve the current app and design tokens. Add mode selector labels Existing workflow, Local agent test and BAND collaboration, plus separate transport and source badges. Render a side-by-side purchase/source comparison, accepted actor timeline, validated evidence questions, and existing local packet controls. Use existing polling at 800 ms; no new socket infrastructure. Add stable selectors `diwali-mode`, `agent-timeline`, `source-mode`, `transport-mode`, `model-comparison`, `challenge-reason`. Never animate invented messages or expose raw model output. No redesign, new chart library or generated executable UI.

**No fake sponsor states:** if an A2A session is replayed, prominently label it “Recorded collaboration replay” with capture time and source run ID; never animate prerecorded messages as though live. A successful deterministic fallback is a working product but not proof of a live BAND/Lyzr interaction.

## 6. Runtime budgets, retries and failure policy

**Locked bounds:** one active run, one active case, maximum five fixture products, at most ten candidate records considered per product and only the baseline supported notice normalized automatically. Multiple supported competing candidates require review rather than a new general matching engine. V2 run deadline is 90 seconds; reserve the last five seconds for cancellation/finalization. No-key tests use an injected clock and network denial. Live latency under 45 seconds is an optimization target, not an invented guarantee.

- Remote task budget: 10 seconds, capped by remaining run time. At most one retry for a safe public GET, within that same budget. No automatic retry of Lyzr inference, sandbox provisioning or an unknown-outcome external write. Prewarm/provision outside the judged run with a separate 120-second ceiling, and reconcile unknown provisioning outcomes before another request.

- End-to-end real-time demo target: **under 45 seconds** with warm agents and cached official source. This is a performance goal, not an assertion until measured. Local replay should be immediate and deterministic.

- Maximum one public-source follow-up per case, 12 unique application messages per case, and three Lyzr calls per run. Explicit mismatch and missing purchase-model cases do not need an LLM call. Do not extend budgets to make a failing test or slow provider appear successful.

- Preserve the existing run-status vocabulary: queued, running, completed, partial, failed. Fallback is provenance, not a new status. A completed analysis can legitimately contain rejected or needs-review products. A failed enabled sponsor marks the run partial even when deterministic findings remain usable. A BAND outage never becomes a completed local collaboration.

- Unique message IDs and unique logical task-result keys deduplicate delivery. Same ID/same digest is ignored; same ID/different digest is rejected and audited. A late, wrong-phase or wrong-revision response cannot change state. Record outgoing intent before send, then receipt and consumption; do not claim exactly-once network delivery.

- Agent must see source facts; source-URL research and LLM responses never receive system/tool privileges. Validate domains, redirect targets, resolved IPs and outgoing request restrictions before network calls.

- Protect sensitive consumer data: use synthetic fixtures for event demos, redact order IDs, hash uploaded documents, never expose receipt images or API keys in logs/BAND rooms/Agent37/Finch packages.

- Disable remote features by default on the existing shared public demo; use separate staged secrets/instance where possible, and enforce budget caps.

- Failure injection must retain correct rejection/uncertainty, an explicit partial/failed run, and an option to start a separately identified deterministic fallback. Never complete a positive packet with missing authoritative evidence. Recorded replay is read-only: it cannot reapprove, re-export through a mutating route or trigger provider work.

**Application configuration additions:** these names belong to Sueperman, not vendor SDKs. The per-provider lock records verified SDK configuration mappings. Keys and identity credentials stay in an ignored owner-only file; the application example contains no secret values.

```dotenv
DIWALI_ENABLED=false
DIWALI_COLLABORATION_MODE=deterministic
DIWALI_LIVE_AUTHORIZED=false
DIWALI_PROVIDER_LOCK=harness/diwali/provider-contracts.lock.json
BAND_ENABLED=false
BAND_CREDENTIALS_FILE=
LYZR_ENABLED=false
LYZR_API_KEY=
LYZR_REVIEW_AGENT_ID=
FINCH_ENABLED=false
FINCH_SKILL_PATH=
FINCH_SKILL_SHA256=
AGENT37_ENABLED=false
AGENT37_API_KEY=
AGENT37_INSTANCE_ID=
DIWALI_MAX_MESSAGES_PER_CASE=12
DIWALI_MAX_FOLLOWUPS_PER_CASE=1
DIWALI_MAX_LYZR_CALLS_PER_RUN=3
DIWALI_REMOTE_TASK_SECONDS=10
DIWALI_MAX_RUN_SECONDS=90
DIWALI_ALLOW_RECORDED_REPLAY=true
```

The authorization flag records a real owner authorization; setting it is not permission to spend. Validate missing identity/configuration before work. The operator supplies an authorized sandbox ID after provisioning; startup must never create paid infrastructure automatically.

Use actual vendor configuration names where SDKs require them. Keep .env.example empty of secrets. Do not log or commit live keys; UI flags show real provider health, not mere configuration.

## 7. Milestones and Codex execution order

**Foundation — G0–G3, first invocation:** establish baseline, frozen oracle, local actor behavior, persistence and UI. This is explicitly not live sponsor proof.

1. G0 records the repository boundary map, baseline tests, fixture hashes and API shape. Run documented checks against an isolated database. Existing failures are recorded separately; do not silently fix unrelated code or reuse historical slide-deck test counts.

2. G1 creates acceptance.json, frozen expected.json and the gate runner before runtime implementation. Tests must fail for the intended missing behavior, not only an import error. Frozen expectations and baseline safety tests cannot be edited to make implementation pass.

3. G2 implements four actor handlers, pure reducer and no-network local transport. Assert exact golden results and meaningful message traces before any BAND dependency is installed.

4. G3 wires the coordinator, additive tables, compatibility facade and existing API. Test transaction rollback, duplicate messages, stale evidence and process restart. The new run path cannot call the V1 orchestrator and then fabricate a second agent trace over its results.

5. Finish G3 with the bounded UI additions and Playwright acceptance. Run the unchanged V1 suite and offline V2 gate suite. Stop this invocation with gate evidence, unresolved blockers and the exact next target; do not proceed to paid integrations automatically.

**Sponsor gates — G4–G7, bounded subsequent invocations:** one provider contract at a time. The core sponsor target is G4 BAND plus G5 Lyzr. G6 and G7 extend coverage without changing the domain contract.

6. G4 proves BAND custom-adapter transport and all four identities. G5 adds the single Lyzr review client. Pin observed SDK/API contracts, validate a real round trip and rerun the unchanged local suite after each provider.

7. Verify the existing G3 Builder now receives BuildRequested over BAND and returns BuildReport. Its output remains typed view data plus a local draft—not a dynamically generated website. Show a separate evidence-gap case where a valid reviewer request leads to one research follow-up; do not force the model to produce a scripted answer.

8. G6 packages, verifies and loads the pinned Finch skill. External publication and retrieval require authorized access. Local skill evaluation may PASS while Finch proof remains BLOCKED or IMPLEMENTED_UNVERIFIED; report both.

9. G7 invokes the same public-research contract in an authorized Agent37 sandbox. Verify provision/reuse, execution, result validation and teardown independently. No API guessing and no migration of the core application.

10. After each sponsor gate, rerun offline acceptance and V1 regression. A sponsor blocker does not invalidate passing independent gates, but no required live proof can be replaced by a skipped test. G6/G7 may run independently once their own declared prerequisites pass.

**Release — G8–G9:** G8 prepares real recordings, AdaL handoff assets and reproducible build evidence. G9 verifies actual provider executions, final video and the authorized submission/deployment. Presentation requirements are not optional stretch work.

11. Capture clean real browser footage for a 110–115-second edit. Create final version in AdaL; inspect audio, captions, MP4 playback, duration and provenance.

12. Test public staging URL end-to-end in normal/incognito browser. Check README quickstart, public GitHub repo, no exposed secrets, and one-click demo dataset. If existing DigitalOcean deploy is shared, avoid disrupting it; use an isolated preview if feasible.

13. Prepare fallback prerecorded demo clearly labeled “replay” and make sure public app and video agree on capabilities.

14. Update docs/DIWALI_SPONSORS.md truthfully; freeze features, tag an explicit candidate, upload video/repo/links before deadline.

**Scope exclusions:** no extra actors, agent framework, auth project, generic settlement engine, receipt expansion, new database, UI redesign or speculative analytics. If time/access blocks maximum sponsor coverage, defer G7 then G6 while retaining G4/G5, all safety gates and AdaL submission work. Never lower the acceptance threshold. The handoff must state which sponsor remains unproven.

## 8. Test suite and measurable acceptance gates

**Golden-path regression (must preserve V1):**

- PB22 matches documented affected model and produces exactly one source-cited real recall draft; PB23 is rejected and cannot produce a positive packet; missing model is NEEDS_REVIEW; bottle has no false positive; fictional settlement remains prominently simulated.

- All positives have authoritative URLs, fetched-at timestamp, source type and rule facts. No fabricated remedy, refund, guaranteed settlement or submitted-claim status.

- Existing local approval/export works and stale evidence invalidates previous approval. Two seed/reset runs yield identical outcomes and no duplicate case rows.

- No external claim submissions or money movement. V2 sponsor demonstration accepts only the pinned synthetic dataset; verify its content digest, not just a demo flag. Do not claim private multi-user isolation in the existing unauthenticated V1 app. Live V2 is operator-run; unattended public V2 displays fixture/replay data without a paid-run or reset action.

**A2A acceptance (new):**

- Four distinct authenticated BAND identities, with real messages received and consumed in the positive case. An exact-match negative case terminates before builder. Test transport must produce the same domain outcome without being labeled BAND.

- One Lyzr inference response is validated and causes a subsequent action, question, or challenge; a manually typed Lyzr-looking JSON blob does not count.

- The PB23 negative input yields a Skeptic ChallengeRaised with exact compared model values and a deterministic final REJECTED; PB22 yields positive match with no invented constraints.

- Missing purchase model yields one user question and NEEDS_REVIEW, with zero web follow-ups. Missing official-source facts permit at most one follow-up. Both branches have explicit termination tests.

- Correlation/message IDs persist; duplicate delivery is idempotent; delayed responses after terminal completion are safely ignored.

- Disabled optional providers are not failures. An enabled provider that fails is reported as degraded with a partial run; BAND loss or mandatory source loss closes incomplete work without claiming success. A separate user-started deterministic run can reuse valid inputs, never silently relabel prior results.

- Finch skill, if claimed, is demonstrably executed in a real case and its version/fingerprint is recorded. Agent37, if claimed, has observed provision, execution, sourced result and teardown.

- AdaL-created MP4 is playable, contains true application footage and stays below the 120-second event limit.

**Security/privacy acceptance:** reject prompt injection from manufacturer pages, forged official URLs/redirects, private-IP SSRF, overlarge messages/files, malformed JSON schema, invalid sender identities, leaked tokens, replay masquerading as live, and unsupported legal claims. Screenshot/video contain only synthetic data.

**Engineering evidence:** expand pytest/unit/browser workflow tests, not just mocks. Run **make test lint typecheck build** and **make smoke e2e** under the actual repo's documented port settings. Collect stdout/exit status + passing test counts + working public URLs in docs/evidence/diwali/. Tests that assert only mocked provider contracts are PARTIAL integration proof.

**Ready-for-judging definition:** no-key baseline green; real BAND trace; live Lyzr trace; source-cited PB22/PB23 contrast; human-reviewed packet export; clearly labeled sponsor states; AdaL MP4 <120s; public repo; public site or reliable local fallback; timed rehearsal; truthful sponsor evidence matrix. Four/five sponsor badges are not a substitute for this gate.

## 9. Two-minute judge demo — sequence and proof

**00:00–00:15 — Human problem:** “A real CPSC recall can affect a purchase you forgot you made. Sueperman checks your purchase history and turns verified remedies into next steps.” Show official NEWDERY notice and a synthetic five-item list.

**00:15–00:35 — Agent delegation:** start run; Case Manager delegates to Researcher in real BAND room; show Researcher using official source and emitting a structured report. Name the key sponsor only if genuinely live.

**00:35–00:60 — Killer moment:** Skeptic receives PB23 vs PB22, raises ChallengeRaised, and deterministic gate records **REJECTED — MODEL MISMATCH**. Then show PB22 matches. Put the challenge and resolved outcome side by side.

**01:00–01:20 — Build value:** Builder turns sourced research into interactive evidence/eligibility panel and a prepared local remedy packet; click official reference, show documentation checklist and safety instructions, approve locally/export (never submit).

**01:20–01:40 — Sponsor proof:** in a compact run-details drawer show REAL BAND room, Lyzr inference, Finch version (only if proven), Agent37 sandbox execution (only if proven), and per-provider timestamps, without delaying the main demo.

**01:40–01:55 — Credibility and close:** one source-cited matched recall, one rejected near-match, one needs-info result, privacy and human control. “It doesn't guess who deserves money. It knows when to say yes, no, or I don't know.”

**01:55–02:00 — Final card:** Sueperman URL, public repo, one-sentence impact. Keep the exported AdaL video shorter than 120 seconds to allow codec/player variance.

**Do not narrate all five platforms for equal time.** The product, real agent challenge and proof of trust are the narrative; integration names are secondary evidence.

## 10. Risk register and fallback decisions

| Risk | Locked response |
|---|---|
| Eligibility provenance | Record the owner's confirmed eligibility; do not invent organizer correspondence or block the build |
| BAND SDK mismatch | Pin/probe a custom adapter; stop that gate after bounded failed hypotheses |
| Lyzr malformed or unsupported output | Reject schema/reference violations; no eligibility override or automatic repair call |
| Finch access/signing | Continue local package tests; block external proof pending authorized publication |
| Agent37 unknown provisioning outcome | Reconcile owned resources before retrying; verify deletion separately |
| Latency | One case at a time, shared public-source cache, fixed deadline and honest recorded footage |
| Source unavailable | Explicit partial result; separately labeled fixture demonstration only |
| Interrupted write | Transactional finalization, startup reconciliation, no automatic paid task replay |
| Public privacy/spend | Pinned synthetic dataset and operator-only live mode; no unsupported tenant-isolation claim |
| Scope growth | Gate-specific path allowlist, unchanged oracle, no unrequested infrastructure |

## 11. Live event action checklist and deliverables

- [ ] Record owner-confirmed eligibility and pre-existing/new-work attribution without fabricated approval details.

- [ ] Fresh baseline check (commit + tests + working demo) completed.

- [ ] Four BAND identities show actual send, receive and consumed result; local transport remains separately labeled.

- [ ] Lyzr real specialist call validates and affects a case decision/question.

- [ ] Research → Skeptic → Builder flow produces a real interactive result.

- [ ] PB22/PB23/unknown-model demonstrations pass with official citations.

- [ ] Finch skill loaded/executed and Finch-specific acquisition/publication proof captured, if feasible.

- [ ] Agent37 sandbox invoked and shut down; public evidence returned, if feasible.

- [ ] Public deployment or preview reverified with sponsor flags/cost controls.

- [ ] AdaL-rendered MP4 has real footage, audio/captions and runtime <120 seconds.

- [ ] Sponsor proof sheet links to actual evidence artifacts, including honest PARTIAL/NOT PROVEN rows.

- [ ] Existing and new tests, security checks, quickstart and public repo verified.

- [ ] Submitted public repo, video and demo link before November 18, 6 PM Pacific.

- [ ] Prepare finals presentation and questions for November 19 if selected; use the organizer-confirmed presentation length rather than assuming three minutes.

## 12. Official implementation references

- Event, deadline, rules, sponsors: https://luma.com/bc8etq9q

- BAND SDK/version/adapters: https://docs.band.ai/sdks and https://docs.band.ai/reference/sdk

- Lyzr current chat request/response contract: https://docs.lyzr.ai/enterprise/api/agents/chat

- Finch skill publication and consumption: https://www.finchtech.ai/en/story/publish-skills and https://www.finchtech.ai/en/story/use-skills

- Agent37 Cloud/API and sandbox behavior: https://www.agent37.com/cloud

- AdaL video producer and OS requirements: https://docs.sylph.ai/features/video-producer/

- CPSC recalled NEWDERY product: https://www.cpsc.gov/Recalls/2026/NEWDERY-Power-Banks-Recalled-Due-to-Fire-and-Burn-Hazards-Risk-of-Serious-Injury-Sold-on-Amazon

- Existing repo/docs: https://github.com/nirmalhk7/sueperman

## 13. Copy-to-Codex first prompt

> **First invocation — TARGET_GATE=G3; LIVE_CALLS=disabled.** Implement Sueperman V2.1 gates G0–G3 only in the existing repository. Preserve the working branch and all unrelated changes. Read applicable repository instructions and this contract; inspect only the boundary files needed for the selected gates. Freeze the baseline, required outcomes and protected paths, then write tests before the corresponding runtime changes. Build exactly four actors with local transport, a pure reducer, coordinator-only persistence, backward-compatible run API and the specified UI additions. Use the existing matcher and composer; never weaken safety tests or regenerate expected outputs to match broken behavior. Run every required gate check without skip/xfail. Stop after G3, or at a critical failed prerequisite, and write the §14 handoff with actual command results, remaining blockers and next target G4. Do not install sponsor stacks, invoke paid APIs, push, publish or deploy in this invocation.

> **Subsequent invocation template:** TARGET_GATE=G4 (replace with the requested gate). Read the saved baseline, provider lock and latest verified handoff; revalidate changed prerequisites. Implement only that gate and its unfinished required prerequisites. LIVE_CALLS remain disabled unless explicitly authorized for the named provider and budget. A missing external capability produces BLOCKED, not a substitute provider. Stop at the selected gate with evidence.

**Before launch:** place the full current page in `docs/DIWALI_SPEC.md` or attach it to the coding session. A page URL alone is not a guarantee that the coding environment can read its contents. Preserve the original V1 SPEC. The owner can authorize a larger gate range explicitly; the default is not an open-ended build.

## 14. Executable acceptance contract

### 14.1 Scope and sources of authority

This section defines the implementation acceptance policy. Do not maintain a competing P0/P1 checklist. Applicable repository instructions, explicit owner permissions and safety constraints still apply. For product behavior use the frozen V1 baseline plus this V2 contract; for a vendor interface use the verified provider lock. If these conflict, report the smallest conflicting requirement and stop the dependent change rather than choosing silently.

Keep durable instructions short. The full design belongs in `docs/DIWALI_SPEC.md`, not a giant root AGENTS.md. Preserve existing AGENTS.md files. Record only task-specific invariants, gate commands and document pointers in a scoped instruction file when needed. Do not create a new planning document at every checkpoint.

### 14.2 Minimal harness and frozen oracle

Create `harness/diwali/` with five small machine-readable files: `baseline.json`, `acceptance.json`, `expected.json`, `provider-contracts.lock.json`, `handoff.json`. Add `scripts/verify_diwali.py` and gate tests under the existing test layout. These are requested deliverables, not files claimed to exist already.

`baseline.json` records HEAD, dirty-path inventory, protected file digests, lockfile digests, test commands/results and a narrow symbol map for run dispatch, matcher, composer, persistence and UI integration. Inspect the actual repository instead of inventing imports. In the reviewed code, `app.agent.orchestrator.persist_recall` and `event` commit internally; verify that remains true before choosing the integration boundary.

`acceptance.json` maps requirement ID → gate → executable test node or verifier → expected assertion → evidence path. `expected.json` contains manually specified expected facts from the table below, with no calls to the implementation to manufacture the expected side. Freeze both before runtime work. A discovered specification error requires a visible contract-change record and owner decision; it is not repaired by weakening the oracle.

| Fixture | Required final behavior | Builder/draft rule |
|---|---|---|
| DEMO-001 / ZHX-PB22 | verified_match for the recorded supported recall; all existing required gates pass | One real-recall draft, never approved automatically |
| DEMO-002 / ZHX-PB23 | rejected with exact compared models and a MODEL_MISMATCH challenge | No builder task and no positive packet |
| DEMO-003 / bottle | No recall opportunity within supported fixture scope | No builder or packet |
| DEMO-004 / absent model | needs_review and one question for the purchase model | No web follow-up, builder or positive packet |
| DEMO-005 / earbuds | Existing simulated settlement outcome, visibly fictional | Excluded from real-remedy/draft counts |

Normalize only nondeterministic identifiers, timestamps and durations when comparing fixtures; do not remove status, reason, source, model, approval or provenance fields. Inject clock/ID providers for tests. Use the fixed fixture evaluation date for recorded settlement replay and current UTC for live deadline checks. Preserve original fixture files and their hashes. The baseline five-product behavior must still pass with DIWALI_ENABLED=false.

### 14.3 Contract surfaces and actor traces

New implementation paths are confined to `services/api/app/diwali/`, its tests, the two specified UI components, `harness/diwali/`, the verifier script, skill package and DIWALI documentation. G0 lists the exact legacy integration files before editing: run dispatch/schema, configuration, app registration/database setup, existing run view and Makefile. Additional legacy edits require an explicit reason in the change manifest; unrelated cleanup is prohibited. No new runtime framework or dependency upgrade. Add sponsor dependencies only at their provider gate with a narrow lockfile diff.

Business message payloads are discriminated, typed and closed:

| Message pair | Route | Required payload |
|---|---|---|
| ResearchRequested / ResearchReport | manager ↔ researcher | Frozen product reference / normalized candidate references, coverage and truncation |
| ReviewRequested / ReviewReport | manager ↔ skeptic | Frozen product plus evidence references / rule result, conditions, compared identifiers, challenge code, bounded review note and requested fields |
| FollowUpRequested / FollowUpReport | manager ↔ researcher | Missing public fields and approved source references / new validated facts or explicit unavailable reason |
| BuildRequested / BuildReport | manager ↔ builder | Verified assessment and input digests / unsigned draft, typed view data and matching digests |
| TaskFailed | assigned actor → manager | Fixed reason code and retryability; no raw exception or secret |

No actor-to-actor routes outside this table; the manager handles delegation through actual messages. An immutable report may include compact normalized public facts alongside references so remote actors do not require database access. A reference to another run, wrong source digest or unauthorized sender is rejected before a handler executes.

Golden positive trace has six application messages: research request/report, review request/report, build request/report. Negative and missing-purchase-model traces have four. The bottle no-candidate path has two. One public-source follow-up adds four messages: follow-up request/report and second review request/report. Transport acknowledgments and audit events are counted separately. Ordinary logic must use product/evidence facts, not DEMO IDs, to choose outcomes.

### 14.4 Reducer and terminal states

Implement `reduce_case(state, accepted_message) -> (new_state, commands)` as a pure function. It performs no I/O, reads no environment variables and uses no implicit wall clock. Manager executes returned commands through injected adapters. Separate workflow phase from domain outcome.

| Current phase | Accepted result | Next action |
|---|---|---|
| NEW | Start command | RESEARCHING and ResearchRequested |
| RESEARCHING | No supported candidate | Finalize NO_MATCH, without a global safety claim |
| RESEARCHING | One supported candidate | REVIEWING and ReviewRequested |
| REVIEWING | Explicit trusted exclusion | Record ChallengeRaised; finalize REJECTED |
| REVIEWING | Missing purchase fact | Finalize NEEDS_REVIEW with one user question |
| REVIEWING | Missing public fact; follow-up unused | FOLLOWUP and FollowUpRequested |
| FOLLOWUP | Facts or unavailable reason | REVIEWING once; unresolved evidence finalizes NEEDS_REVIEW |
| REVIEWING | All required conditions verified | BUILDING and BuildRequested |
| BUILDING | Valid draft with current digests | FINALIZING, then DONE after commit |
| Any nonterminal phase | Deadline, restart, invalid required provider result | Close affected work with failure/degradation reason; no invented result |

DONE cases never change from late messages. A response must match task, expected revision and current phase. Case revision increments only when an accepted state transition commits. Same message ID and same digest is a no-op; conflicting reuse is a protocol error. Distinct message IDs for the same completed task cannot cause another side effect.

Final run status is completed only when required work reached terminal results without operational failure. Rejection and uncertainty are valid analysis results. Use partial when some valid results survive an operational failure, otherwise failed. Disabled optional sponsors are not failures; failed enabled sponsors remain visible and cannot claim PROVEN.

### 14.5 Persistence and restart boundary

Use one coordinator and serialized case finalization. No database session crosses an await or actor boundary. Persist outgoing task/message intent in a short transaction before external send. Record delivery and accepted consumption separately. A transaction must couple an accepted response, its revision change and newly scheduled intent so a duplicate cannot replay the transition.

**Do not call legacy helpers that commit internally inside a purported outer atomic transaction.** Implement `diwali/legacy_bridge.py` as a narrow persistence facade using the existing ORM models, pure matcher and composer. Persistence glue may be adapted; eligibility and source-policy logic must not be copied or changed. This facade stages domain rows, packet status and final audit event in one explicit transaction. Baseline-parity tests protect legacy behavior. Do not run the entire V1 workflow first and label its completed results as agent collaboration afterward.

Store the frozen evidence in the V2 case even if legacy SourceEvidence rows are later replaced. Bind draft approval to current purchase/evidence digests. Before finalization compare current input digests with the case snapshot; changed inputs invalidate the draft and return NEEDS_REVIEW/STALE_INPUT instead of approving stale work. A failure before commit rolls back the complete finalization. Never mark a case DONE before its packet/outcome commit succeeds.

Startup marks interrupted V2 runs partial or failed and pending tasks cancelled. Do not automatically rerun paid/model/provisioning calls or send old outbox tasks. A new explicit run can reuse confirmed input snapshots. A provisioning call with unknown outcome is reconciled separately against owned resources before any replacement is created.

### 14.6 API compatibility and modes

Preserve V1 endpoints, response status vocabulary and omitted-field behavior. In the run idempotency check include the normalized new collaboration_mode and fallback_of fields as well as the existing inputs. Same key/same effective request returns the original run; same key/different effective request returns 409. Check idempotency before performing remote work. Preserve the existing single-active-run rule.

Use distinct provenance axes: transport = deterministic/local/band; source = live/recorded/fixture; reviewer = rules/lyzr/fixture; and optional provider statuses. Live BAND transporting a recorded CPSC notice is **BAND LIVE / SOURCE RECORDED**, not fully live research. Store requested and actual modes separately; actual mode comes from the adapter. Captured replay is read-only and cites its original capture time/run. A golden fixture transcript is LOCAL TEST, not evidence that a past live run occurred.

No sponsor-enabled V2 upload flow for real private receipts in this release. Verify the exact pinned synthetic fixture content before a BAND run. Keep publicly accessible V2 demonstrations replay/fixture-only unless an operator explicitly runs the bounded live session. Do not add authentication or promise multi-user privacy as part of this hackathon patch.

### 14.7 Provider lock and controlled uncertainty

For every provider record documentation URL and retrieval date, chosen package/version, exact request/response interface, authorization mechanism by name only, model/agent configuration digest where applicable, timeout, schema and captured sanitized probe. Missing details remain null with a blocker; do not fill them from memory. A successful import/configuration check is not a live round trip. Re-probe when a locked interface changes.

Pin model and prompt/skill configuration where supported; record unpinnable remote changes as limitations. Temperature zero or a seed is not a determinism guarantee. Golden tests use recorded/test adapter data; live tests assert invariants and schemas, not identical prose. Test both empty and nonempty valid review questions; never force a live provider to return a predetermined line to make the demo pass.

The Lyzr reviewer may request at most two allowed missing public fields. Manager filters out already-known fields and follows only approved official sources once. It cannot ask for private identifiers, create URLs or change eligibility. Its validated note can be displayed as a review note, separate from authoritative facts. Finch proof requires the retrieved package digest to match the loaded prompt context. Agent37 proof requires a consumed result, not only an instance ID.

### 14.8 Gates and dependency graph

| Gate | Depends on | Required exit evidence |
|---|---|---|
| G0 baseline | None | Observed HEAD, protected paths, boundary symbols, reproducible V1 checks or an explicit baseline blocker |
| G1 oracle | G0 | Frozen expected outcomes, requirement/test map, runner that fails on a deliberate violation |
| G2 local core | G1 | Four actor handlers, pure reducer, all five fixture results, network-denied tests |
| G3 app slice | G2 | Transaction/API/UI wiring, regression parity, rollback/restart/duplicate tests, browser evidence |
| G4 BAND | G3 | Pinned SDK contract, four authenticated identities, actual delivered and consumed messages |
| G5 Lyzr | G3 | Pinned chat contract, safe schema handling, actual inference consumed in review; integrated BAND proof additionally requires G4 |
| G6 Finch | G5 | Valid package and tests; actual retrieved Finch package loaded in a real reviewer invocation for sponsor proof |
| G7 Agent37 | G3 | Verified lifecycle contract, authorized task, validated public result and cleanup; full A2A proof additionally requires G4 |
| G8 release assets | G3 | Reproducible build, truthful footage manifest, AdaL editing handoff and tested video validator |
| G9 release audit | G4, G5, G8 | V1/V2 gates rerun, combined live trace, actual AdaL MP4 under 120 seconds, public artifacts checked; report G6/G7 status separately |

Default first invocation stops at G3. Subsequent invocations receive a named target gate or range. Do not stop after every trivial file edit or repeatedly ask architecture questions already resolved here. Do stop on an unsatisfied mandatory dependency, protected-path conflict or missing required authorization. A blocked independent sponsor does not prevent unrelated gate work explicitly within the requested range. A release claiming all five sponsors additionally requires actual G6 and G7 proof.

### 14.9 Executable checks and anti-shortcut rules

Implement `make diwali-check GATE=G3` as a wrapper around `scripts/verify_diwali.py --through G3 --offline`. The Python verifier returns 0 for PASS, 1 for FAIL and 2 for BLOCKED; Make is only required to preserve a nonzero failure signal. Add an explicit opt-in `make diwali-live-check PROVIDER=band`; it must refuse without real authorization/configuration. No live calls occur in ordinary test, lint, typecheck, build, health or offline gate commands.

Before runtime coding, map these requirement IDs to named tests. They are mandatory assertions, not a target test-count metric:

| IDs | Required checks |
|---|---|
| D01–D05 | Five golden outcomes, exact source/model evidence, exactly one real recall draft and no auto-approval |
| D06–D08 | Four role identities, exact positive/negative traces, same domain output from the local contract and recorded transport adapter |
| D09–D12 | Duplicate delivery, conflicting duplicate, wrong sender/revision and terminal late message cannot change state |
| D13–D15 | Missing purchase model requests user input; missing public fact permits one follow-up; second unresolved review terminates |
| D16–D18 | API default compatibility, idempotency collision across modes and unchanged V1 feature-off behavior |
| D19–D22 | Transaction failure rollback, restart cancellation, stale evidence invalidation and no repeated external side effect |
| D23–D26 | Invalid Lyzr JSON/reference/tool instruction rejection; source injection/SSRF rejection; no-key network denial; no unapproved export |
| D27–D29 | Correct transport/source badges, UI error/empty states and real browser packet workflow |
| D30–D32 | Provider proof derives from artifacts, required tests cannot skip/xfail, evidence tied to tested commit/config |

Every mandatory node must actually run. Zero tests, missing tools, skipped tests, xfail or a swallowed subprocess error cannot yield PASS. Keep stdout/stderr, exit code, duration and command for each check. Existing `make test`, lint, typecheck, build, smoke and e2e remain mandatory at the app/release gates under documented ports; start only task-owned processes, use a disposable database and stop only those processes.

Test the tests in an isolated working copy with targeted mutations: make PB23 pass, turn unknown into verified, bypass approval, consume the same message twice, suppress a provider failure, or falsely label local transport BAND. Each corresponding test must fail; restore the mutation and rerun. Also change irrelevant demo IDs, reorder candidate input and normalize permitted case/whitespace to detect hardcoded fixture-ID outcomes. Do not change punctuation/suffix matching rules. Never leave mutation code in the delivered branch.

### 14.10 Finish and resume without drift

For each gate use: write the assertion → observe the intended failure → implement the smallest change → run targeted checks → run declared regressions → review the diff → save evidence. No blind three-attempt loops: each repair must cite a distinct failure hypothesis. After two unsuccessful repairs to the same external contract, preserve the working state and record BLOCKED rather than installing another framework.

Handoff is machine-readable and concise. It includes `spec_version`, `target_gate`, `baseline_commit`, `tested_commit_or_tree_digest`, `gate_results`, `commands`, `artifact_paths`, `changed_paths`, `protected_files_unchanged`, `provider_proof`, `blockers`, `next_gate` and `resume_instruction`. Each blocker names the missing capability, attempted evidence and minimal owner action; never include credentials. Do not set PASS from self-review prose. The runner derives it from required outcomes and unskipped checks.

On resume, inspect the saved handoff and current diff, verify protected hashes and rerun only prerequisites invalidated by intervening changes. Do not regenerate plans, reinstall everything or repeat successful paid calls solely because the conversation restarted. No success claim for code, provider usage, deployment or video without its corresponding observed artifact.

**Acceptance distinction:** G0–G3 can be implementation-complete offline. G4/G5 establish the core live sponsor story. G6/G7 expand verified coverage. G9 establishes submission readiness. These labels are never interchangeable.

**Workflow references:** [OpenAI Codex phased-workflow guidance](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex) and [guidance on focused instructions](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra). The gate names and file layout above are project conventions, not required Codex features.

**FINAL GOAL:** The product wins attention because collaborating agents find, challenge, verify and build a safe consumer remedy action plan. Five genuine sponsors can reinforce that story; none is allowed to compromise the original reliable product.

**End of V2 implementation contract.**


