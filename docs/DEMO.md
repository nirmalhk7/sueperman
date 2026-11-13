# 90-second demo

Run `make setup`, then `make dev`. If another app owns 3000, use `make dev WEB_PORT=3001` and open http://localhost:3001.

1. 0–10s: Open Sueperman. Explain old purchases may have remedies people miss.
2. 10–20s: Click **Try demo data**. Five synthetic rows appear. Click **Check my purchases**.
3. 20–45s: Open **Recall matched**. Compare ZHX-PB22 with official affected model, inspect linked CPSC notice and observed-at time. State this is offline replay, not a fresh live check.
4. 45–60s: Open **Not affected** for ZHX-PB23. Show **REJECTED — MODEL MISMATCH**. Missing model instead needs information.
5. 60–75s: Return to exact match; **Prepare claim packet**, inspect missing evidence and safety instructions. Check review box, **Approve draft locally**, **Export Markdown**. Approval does not send anything.
6. 75–85s: Open **Simulated settlement**. Point out **SIMULATED CASE — NO REAL CLAIM AVAILABLE**.
7. 85–90s: Show activity and provider modes. Claims prepared, never fabricated.

Use CPSC source for current manufacturer instructions; do not claim Bright Data ran unless sponsor evidence records an actual invocation. No refund or external submission is demonstrated.

## P1 live extension (separate from fixed five-row replay)

Start with `BRIGHTDATA_ENABLED=false OPENAI_ENABLED=false make dev WEB_PORT=3001` while Bright Data activation is pending. Keep configured keys in ignored `.env`. For this account set `GEMINI_MODEL=gemini-3.5-flash-lite` because 2.5 returns 404 for new users.

Upload `demo/receipt-synthetic.png` or `.pdf` (visibly synthetic test receipts). Review the suggested model, check the confirmation box, and confirm identifiers. Choose Live APIs, run the imported receipt, review live CPSC evidence and selected action, then locally approve/export a packet. Duplicate uploads reuse existing extraction.

A separate synthetic Kroger transaction exercises the verified case in the opt-in live browser suite. Show LIVE verified settlement sources, December 21, 2026 deadline, primary administrator/court citations, and Personal eligibility unconfirmed. Prepare only an information draft; review missing insurance, geography, exclusions and proof. Local approval/export sends nothing.

`P1_LIVE_E2E=1 WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test tests/p1-live.e2e.ts` is opt-in because a fresh database can invoke Gemini twice (1,024 output tokens per call, no retries). Ordinary `make e2e` skips these paid/live checks. Live evidence and screenshots: `docs/evidence/p1-*.json`, `output/playwright/p1-live/`.
