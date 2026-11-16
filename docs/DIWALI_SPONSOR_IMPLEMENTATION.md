# Remaining V2.1 sponsor implementation

The owner requested remaining V2 work after main promotion and explicitly selected V2.1/P1 responsibilities. The original linked Page retains older role/status text; that does not reverse the owner's decision. GitHub default branch was changed to main and verified through GitHub on November 15, 2026 Pacific.

## Implementation and executable coverage

| Slice | Files/components and resulting behavior | Acceptance/checks |
| --- | --- | --- |
| G4 task time | `diwali/core.py`, coordinator: explicit injected transition time; each issued task gets its own ten-second deadline | `test_remote_workflow.py::test_each_stage_gets_its_own_ten_second_deadline`; existing golden/reducer tests |
| G4 application transport | `diwali/band_bridge.py`, `band_settings.py`, coordinator, existing run dispatch: four pinned SDK hosts, authenticated receipts, outgoing intent before await, atomic consumption/invocation records, source/transport axes retained | `test_band_bridge.py`, `test_band_api.py`, `test_remote_workflow.py`; D06–D12,D16–D22,D27,R03,R10–R15,R17 |
| G4 credential protection | Pinned SDK compatibility hooks disable initial retry and ongoing reconnect; HTTP error hook stops generated and metadata-specific retries; duplicate dispatch rejected | SDK/socket/HTTP boundary tests; one operator synthetic run only after offline checks; count actual application sends, never treat mocks as proof |
| G5 reviewer | New `diwali/lyzr_review.py`, actor/coordinator injection: one documented v3 inference interface, strict advisory schema, run/case/role session, no POST retry/redirect/repair; local matcher authoritative | `test_lyzr_contract.py`, privacy/schema/adversarial tests; D23,R07,R08,R12,R13,R15; live proof needs new inference authorization |
| G6 auditor | New `skills/sueperman-recall-evidence-auditor/`, bounded archive/pin loader: procedural instructions, existing rule references, synthetic examples; retrieved bytes enter reviewer context only after pin validation | Package/tamper/traversal/secret/executable checks; R06; publication/wallet and actual Finch retrieval remain separately gated |
| G7 worker | New bounded public worker/adapter only after exact documented execution/result/deletion contract is verified | R04,R08,R12,R13,R15; no automatic provisioning or top-up; funded owned instance required |
| G8/G9 release | Real-footage handoff, duration/codec validator and AdaL project/export metadata; retain original assets | R18 and full R01–R18 mapping; no generated scene counts as actual execution, no AdaL claim without actual export; submission/deployment separately authorized |

Full offline regression: `make test`, `make lint`, `make typecheck`, `make build`, disposable app smoke/browser checks and `make diwali-check GATE=G3`. Preserve original baseline, fixture and acceptance files; new provider checks extend coverage without rewriting the frozen oracle. Required live checks remain BLOCKED until their observed artifacts exist. Three paid opt-in V1 browser tests remain outside ordinary offline verification.

## Live limits

Owner: “be careful when doing shit with online creds, max 3 retries. Dont want to use it all up.” Implementation uses zero automatic retries for business POSTs, model inference and provisioning, and zero SDK reconnect attempts. No more than three total attempts are permitted for any live operation; a stricter spec limit wins. A successful message exchange is separate from a retry. One five-case BAND run has eighteen distinct application messages, not eighteen retries. SDK acknowledgements/control reads are separate protocol traffic.

The earlier single Lyzr inference authorization is exhausted. No inference, wallet/signing, skill publication, paid compute provisioning, top-up, deployment or submission is authorized merely by a passing mock test. Existing credentials remain in the ignored owner-only environment; test inputs and evidence are synthetic and sanitized.
