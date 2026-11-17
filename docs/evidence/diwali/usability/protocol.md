# Issue 2 evaluation protocol

Recorded before measurement on November 16, 2026 Pacific. Application revision f7af7ae0c1872e1fe7b925ab70d96d0f6ad35f81. Compare Existing workflow (D) and Local agent test (L) with recorded sources.

## Offline pilot

Run two paired blocks, D/L then L/D, each arm with fresh temporary SQLite, the same five seeded demo purchases, no live providers and the frozen harness/diwali/expected.json oracle. Separately exercise the shared receipt upload and identifier review with the synthetic PNG and PDF and the existing mocked extractor integration check. Seed both comparison arms after that check so receipt extraction cannot change the five-case input. Count per-purchase outcome disagreements and completed arms. Record elapsed milliseconds from run POST through terminal GET with a monotonic clock. Exclude seeding, inspection and export from that interval. Inspect recall evidence and verify preapproval denial, local approval and Markdown export. Report individual measurements, including failures. These are service times and software checks.

## Moderated sessions

Target four adults unfamiliar with the demo, two per order (P01 and P03 D/L, P02 and P04 L/D). Each person tries both workflows independently on the same device with the same fixtures. Use a disposable local instance for each arm with recorded sources and DIWALI_ENABLED=true. Keep live providers disabled. Use synthetic CSV import for the no-key session. After prompt 1, switch to a separate, empty disposable instance and select Try demo data before prompt 2. Demo reset retains non-demo uploads; keeping the import exercise separate ensures exactly five purchases in each scan. No real receipts or external claims.

Give these prompts one at a time. Keep the scoring key out of view. Start the clock when each prompt is read and stop when the participant answers or completes it. Stop at three minutes per task. Record any request for help before assisting.

1. Import demo/orders.csv. Review the purchase list. Which power bank is missing information?
2. Check the purchases in the assigned workflow. Which power bank qualifies for recall review, and why?
3. What would you do with the other power bank whose model is visible?
4. For the power bank missing its model, what information would let you decide?
5. Show the source behind your decision. Was it retrieved today? What does the workflow label tell you?
6. Save a draft for the qualifying item. What has happened outside this app?

Score independently per task. Expected observations are five imported purchases with one missing model, exact PB22 match, PB23 excluded, missing model remains unknown until checked, official CPSC notice replayed from recorded data, and a locally approved Markdown export with no external submission. For prompt 5 score source freshness and workflow meaning separately (existing deterministic processing or local actors). For prompt 4 score uncertainty separately. Count wrong decisions or assertions even if corrected. Record success unaided, assisted, timeout or abandoned. Preserve first answer and correction. Record elapsed seconds, help and short anonymized quotes. Never replace missing data with zero.

Use one row per participant, mode and task: participant code | order | mode | task | status | seconds | mistakes | first answer or action | help/correction | uncertainty / source / workflow scores (correct, incorrect, unanswered, or inapplicable). Compare within-person completion, mistakes, time and comprehension; report order effects and missing rows. Small repeated-fixture sample supports descriptive findings only. For each material defect preserve configuration, steps, expected and actual results for a separate issue.
