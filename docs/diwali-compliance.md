# Diwali V2 compliance and delivery status

Source: [locked V2 specification](https://chatgpt.com/space/page_5e3614ac8e1881919f5c373fb4ee1310), read November 14, 2026 (America/Los_Angeles).

P0 is not release-complete until R01–R18 are accounted for, five actual sponsor executions exist, and the AdaL-produced video passes the 120-second cap. Offline roles are deterministic local replay, never sponsor proof.

## W0 feasibility check

| Sponsor | Verified primary documentation | Local feasibility / blocker |
| --- | --- | --- |
| BAND | https://docs.band.ai/quickstart ; https://docs.band.ai/connect/choose-integration-path | SDK quickstart currently pins 8.1.0. Separate agent identities and addressed mentions required. Four private role identities and room now provisioned; credentials saved locally. Actual SDK handshake remains unverified and SDK version remains untested. |
| Agent37 | https://www.agent37.com/docs/quickstart.md ; https://www.agent37.com/docs/agents-api/exec.md | Documented HTTPS sandbox execution. Key configured; balance observed $0.00. No instance created. Egress policy, pinned worker and lifecycle unverified. |
| AdaL | https://docs.sylph.ai/integration/sdk/overview/ ; https://docs.sylph.ai/integration/sdk/permissions/ | SDK launches authenticated CLI subprocess; deny-by-default callback required. Deferred by user. OS restrictions and live denial unverified. |
| Finch | https://www.finchtech.ai/en/story/use-skills | Signed-in browser download completed for Strategy Red Team v1, Base skill 311, MIT. Published primary fingerprint matched and contents reviewed; recall suitability and actual invocation remain pending. Local rules are not Finch delivery. |
| Lyzr | https://docs.lyzr.ai/enterprise/get-started/concepts/agents | Structured-output Studio agent and stable session required. Builder and standard key created; generated workspace API configuration saved locally. JSON schema validated in Studio and instructions verified in saved Agent JSON. No inference execution or application adapter proof yet. |

Checks inspected presence only; no credential values logged. Documentation read is not execution evidence. No claim submission, organizer message, public publication or sponsor execution proof is claimed; account and agent setup is recorded separately. These blockers do not permit narrowing the five-sponsor target.

## Authorship / submission

Team size and participant names: awaiting actual participant record. Actual local commit metadata is preserved in `docs/evidence/diwali/authorship-history.json`; it does not establish participant membership or organizer eligibility. Specification records team confirmation that code was event-written; independent organizer confirmation not supplied. Preserve actual git history and existing film/slide work without relabeling its timeline. No authorship claim is inferred from the current implementation session.

Event deadline specified as November 18, 2026, 18:00 America/Los_Angeles. Submission channel, per-sponsor prize forms/minimum use and organizer authorship boundary remain external questions. No organizer message, publication or submission authorized here.

## Implementation sequence and verification map

W0 feasibility precedes W1 contracts/ledger, W2 adapter boundaries, W3 offline controller/verifier, W4 API/board, W5 live operational proof, W6 submission assets. W0 live handshakes are blocked; subsequent offline work is provisional, not proof of sponsor architecture.

Definite components: `collaboration/contracts.py`, additive models/migration/ledger, bounded offline roles/controller, opt-in collaboration API, case board, revision-bound local draft/export, behavior tests. Preserve V1 APIs and output files. New route is needed because one case's separate revision history, role outcomes and requested answer cannot be represented by the V1 run page. New additive migration runner is needed because V1 only uses `create_all`. No A2A gateway or Finch publication is authorized or needed for offline progress.

| Requirements | Executable acceptance / required evidence |
| --- | --- |
| R01 | `make test`, `make smoke`, `make e2e`, `make lint`, `make typecheck`, `make build`; existing V1 behavior retained |
| R02, R08, R09 | strict model matching, adversarial result validation, deterministic one-question priority; collaboration behavior tests |
| R03–R07 | role/adapter boundary tests plus separate real BAND, Agent37, AdaL, Finch, Lyzr receipts; offline passes cannot close these |
| R10–R12, R16 | populated V1 migration, historical revisions/drafts, dedup/stale delivery, failures/timeouts/restart tests |
| R13–R15 | typed minimal messages, source allowlist, synthetic-only default, kill switch and bounded calls; no-key API/browser tests plus deployed verification |
| R17 | case board exact/near-match/missing answer/reload and revision-gated export browser checks |
| R18 | actual team/authorship manifest, anonymous repository/video access, AdaL project/export and `ffprobe`; not satisfiable by tests alone |

Five-person usability sessions and agent-value experiments have not been performed. Do not claim measured improvements, independent reasoning or verified live collaboration from deterministic replay.
