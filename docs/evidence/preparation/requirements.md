# Issue 10 acceptance map

The owner approved guidance only, with no private evidence uploads. The existing P1 feature flag controls this slice (`P1_ENABLED=true`); no external identity, storage, model, or document-verification service is required. Public source monitoring has its own existing enablement rules.

The reviewed NEWDERY, Flaunt, iStore, and Baseus document labels now carry preparation guidance. Matching uses exact recall reference, official source URL, and document label. Unreviewed labels or sources stay unknown. Baseus's conditional photo remains unknown because an absent order number in this app cannot establish that the user has none. Optional organizer tips are explicitly separate from official requirements and never become required-document checkboxes.

The guide refers users to the recorded official notice and its safety instructions. It neither invents device-handling/shipping/disposal steps nor supplies declarations, names, markings, or verified evidence. The current source citation, mode, and observation time remain visible. Evidence stays with the user; readiness is local self-reporting. The existing draft's missing-proof fields remain intact.

| Acceptance criterion | Executable evidence |
| --- | --- |
| Guidance only; preserve missing proof and declarations | `test_reviewed_photo_and_declaration_guidance_preserves_missing_proof` |
| Required versus optional organizer tips versus unknown | Same API test, `test_unreviewed_requirement_stays_unknown_instead_of_becoming_official_instruction`, `test_conditional_baseus_photo_is_unknown_until_condition_is_confirmed` |
| Exact reviewed source binding | `test_known_label_at_an_unreviewed_source_does_not_inherit_reviewed_instructions` |
| Readiness remains self-reported and persistent | Existing `test_obligations.py`; P1 readiness browser scenario |
| Source/product/policy changes reset readiness and approval | Existing changed-binding tests plus `test_guidance_policy_change_resets_readiness_and_requires_reapproval` |
| Guidance and citations in exports after reported readiness | `test_preparation_export_retains_citation_and_explicit_guidance_limit` |
| Guidance in exports without any reported readiness | `test_guidance_is_exported_even_when_no_readiness_was_reported` |
| Approvals predating P1 cannot authorize new policy | Two legacy approval/export cases in `test_legacy_approval_cannot_export_new_guidance_until_fresh_approval` |
| Real preparation/reapproval/download UI, desktop and mobile | Extended P1 readiness browser scenario; conditional Baseus browser scenario |
| Rejected stale export can recover through renewed review | P1 reload/reapproval browser scenario with controlled HTTP failure; real SQLite legacy API tests above |

The nine preparation API cases run against the real application and SQLite fixture. The P1 browser harness uses disposable, task-owned servers and recorded CPSC responses; it does not establish live external-provider execution. Its new Baseus response uses the already reviewed `25248.json` fixture. All previous browser scenarios retain their assertions; the runner expects six scenarios instead of four because conditional preparation and stale-export recovery were added.

Application changes are confined to the new `p1/preparation.py`, additions in `p1/obligations.py`, the existing readiness component, and a reload action on the claim page's export error. The guidance policy digest joins the existing approval binding, so a changed guidance policy requires renewed local review. The export includes guidance even when no readiness state exists; in that case it does not invent a self-reported readiness record. Eligible legacy approvals without a P1 binding are downgraded to a reviewable draft, blocking export while allowing a subsequent fresh approval.

Final verification used a clean archive of `be781c8` plus only this issue's eight source/test files. That base already contains the separately committed live-workspace changes. Unfinished issue 9 code and remaining uncommitted work are excluded. `report.json` records every tested file hash; all six final commands confirmed those files stayed unchanged.

Actual final verification: `make test` passed 472 backend tests and 12 frontend tests, including the P1 wrapper running all six browser scenarios. `make lint`, `make typecheck` (67 Python source files plus TypeScript), `make build`, and `make smoke` passed. `make e2e` passed 25 scenarios; three opt-in live image/PDF/settlement acceptance checks were skipped and remain unverified. Smoke/E2E used the existing controlled browser-server fixture on task-owned dynamic ports with mock vendor boundaries. Desktop/mobile screenshots and the actual six-scenario P1 browser log are included. The sole backend warning is an existing Starlette/httpx deprecation warning.

Earlier evidence remains visible: five preparation API tests failed before implementation, the browser failed on the missing preparation heading, and the no-readiness-state export test failed before the review fix. First full-run type checking found an insufficient catalog annotation. Further independent review reproduced export under an unbound legacy approval; two new API cases failed before that repair. The corrected UI regression failed on the old non-recoverable export message before adding reload. The shared fixture now represents a genuinely current approval when P1 schema exists, while explicit legacy cases remove that binding. Monitoring unit fixtures may leave P1 disabled and therefore skip that fixture-only binding query.

The complete final check set was rerun after those repairs. An operator-driver interpreter error occurred after its first four checks; only the two not-yet-run checks were retried in the project test environment. All six final results are retained with unchanged-source guards. The independent reviewer reran 36 focused safety checks, inspected both screenshots and all final records/hashes, and recommended narrow commit and closure. This evidence does not claim container/deployment acceptance or a full release gate.
