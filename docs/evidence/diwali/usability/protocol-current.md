# Current workspace usability protocol

Application revision: `03010a6`. This supersedes the historical walkthrough for future sessions, not its observations. No human sessions have been run under this protocol.

## Sample and configuration

Recruit four adults unfamiliar with this application. Use participant codes only. P01/P03 perform deterministic then agent-team tasks; P02/P04 reverse that order. Each arm gets a fresh disposable database and the same synthetic CSV below. Never use personal receipts, names, accounts, or external claim submission.

Use the controlled vendor boundaries and isolated server configuration in `services/api/tests/diwali/test_ui.py::browser_env` and `services/api/tests/browser_server.py`, pinned to this application revision. They supply recorded public-source responses and synthetic role responses. Keep real credentials, telemetry, and paid providers absent. Unknown external requests must fail rather than fall through to the network. Retain the configuration, actual server ports, source fixture hashes, and any startup failure with each session.

Explain the study boundary before starting: this is a controlled software study, not evidence of live vendor execution or model accuracy. The UI can say “Live” because that configured application path is exercised; the controlled responses do not establish that an external source was fetched today. Score understanding of the displayed label separately from understanding of this study boundary. This briefing limits generalization to unbriefed users.

The current interface has no “Try demo data” control or workflow selector. For D, use **Check my purchases**. For A, use **Investigate with agent team** on the specified purchase row; cases run individually. Tell participants which entry to use, so this is not a workflow-entry discoverability experiment. Measure the complete assigned task, including navigation, rather than comparing one agent case's service time with a deterministic batch.

Receipt image/PDF import and identifier confirmation remain a separate automated preflight using `test_receipt_confirmation.py` and mocked extraction. The no-key human arm uses CSV. Do not claim human receipt-photo extraction usability, real OCR quality, or real provider latency from that preflight.

## Synthetic input

Use `purchases-current.csv`, which has an exact supported model, a near model, and a missing model. It has no simulated settlement. Start each arm empty and import it through **Upload purchases or receipt**. Do not reset another visitor's or another study arm's data. Do not mix these three public-workspace cases with the historical five-case internal replay benchmark.

## Tasks and measurement

Give one prompt at a time. Start a monotonic timer when it is read; stop on the first completed action or answer. Stop each task at three minutes. Record the first answer and every request for help before intervening. Keep the scoring key out of view. Use one observation row per participant, arm and task; leave missing values blank rather than recording zero.

1. Import the supplied CSV and identify which purchase lacks information.
2. Using the assigned workflow, review ZHX-PB22. Explain what matched and what remains unproven.
3. Review ZHX-PB23. Explain why it should not produce a positive remedy draft.
4. Review the purchase missing its model. Explain what information is needed; do not guess or fill it.
5. Find the cited official source. Explain the source/workflow labels and whether this controlled session establishes a fresh external lookup.
6. Prepare the qualifying draft, review it, approve locally and download Markdown. Explain what happened outside the application.

Score completion as unaided, assisted, timeout, or abandoned. Count mistaken decisions even if corrected. Record elapsed seconds, help, first answer/correction, and separate uncertainty, source-label, study-scope, workflow and local-approval comprehension scores: correct, incorrect, unanswered, or inapplicable. Keep anonymous short quotations only with participant agreement.

The scoring key is exact model match, near-model rejection, missing model remains uncertain, an authoritative citation with controlled-runtime limitations, and local approval/download with no manufacturer contact or submitted claim. A matching product is not verified personal evidence or a promised refund. The role preview is an explanation, not execution evidence. Record differences between the deterministic detail view and team case board instead of assuming they offer identical controls.

Expected sample: 48 task observations, four people × two arms × six tasks. Report within-person completion, mistakes, time and comprehension with order effects, missing rows, and assistance. The small repeated-input sample supports descriptive findings only. Do not call software timings participant task times or infer general improvement. Material observed defects need reproducible steps, configuration, expected/actual results and their own follow-up issue.

Use `session-records-current.csv`. Participant recruitment, all 48 human observations, and any human improvement claim are pending. A later application revision requires checking this protocol's controls and configuration before reuse.
