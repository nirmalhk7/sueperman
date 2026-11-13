# Sponsor evidence

Status vocabulary: **PROVEN** requires observed execution and a retrievable local artifact or URL; **PARTIAL** means some implementation/evidence exists but the sponsor's actual live criterion remains unmet; **NOT IMPLEMENTED** means no qualifying integration. Contract tests with doubles are never live proof.

| Category | Status | Evidence and limit |
|---|---|---|
| Best Overall Hack | PROVEN | Local recall discovery, exact-model match, visible excluded near-match, missing-model review, approved-local Markdown download. `docs/evidence/browser-checks.log`, `output/playwright/`. Judge pitch: one purchase history becomes a source-backed remedy checklist. No prize outcome implied. |
| Gemini API | PROVEN | PROVEN live PNG and PDF imports using google-genai with gemini-3.5-flash-lite; `docs/evidence/p1-gemini-api-live.json`, opt-in browser tests `p1-live.e2e.ts`. Identifiers remain suggestions until explicit review. No eligibility or payouts inferred. |
| Bright Data | PARTIAL | Real official MCP initialized with only search_engine and scrape_as_markdown. Search succeeded; manufacturer scrape returned Customer is not active. `docs/evidence/p1-brightdata-status.json`. User will resolve activation; further calls stopped. Manufacturer extraction criterion remains BLOCKED. |
| System One Models | NOT IMPLEMENTED | Current user choice implements the System 1 decision role using OpenAI, not the System One vendor. Legacy contract tests/catalog remain historical evidence only. OpenAI System 1 role made a real request and selected request_user_info; `docs/evidence/p1-model-live.json`. Three-call default budget, four choices, sanitized state and hard-gate override are tested. No System One sponsor claim. |
| DigitalOcean | PROVEN | App Platform deployment ACTIVE, commit 4aee3c3; public HTTPS health/home HTTP 200. [Live demo](https://sueperman-6t4xk.ondigitalocean.app). Public fixture browser plus live CPSC/settlement browser review/export passed. Evidence: p1-digitalocean-deployment.json, p1-digitalocean-public.json, p1-digitalocean-browser.log, p1-digitalocean-live.json and p1-digitalocean-live-browser.log. Paid model/research features deliberately disabled publicly; shared synthetic demo, ephemeral SQLite. |
| Sentry Raffle | PROVEN | Real running-app backend and browser errors received: SUEPERMAN-SERVER-1 and SUEPERMAN-FRONTEND-2. Traces, logs, stored masked replay and readable application frames verified. Evidence and URLs: docs/sentry-setup.md. Local monitoring proof; production Sentry delivery unverified. |
| HyperFrames | NOT IMPLEMENTED | P2 deferred. Browser test recording is ordinary Playwright output, not HyperFrames output. |
| Cleanest Software Factory | PARTIAL | SPEC, test-first components, observed red/green checkpoints, review fixes, final test logs and local commit described in `FACTORY_EVIDENCE.md`. No Whirlwind integration or external judging result. |
| Tiger Data | NOT IMPLEMENTED | P2 deferred; default state stays SQLite. No live write or aggregate claimed. |
| Snowflake | NOT IMPLEMENTED | P2 deferred. No Cortex query or Snowflake connection claimed. |

## Additional authoritative live source

**CPSC REST: PROVEN**. Production adapter queried the official endpoint and returned recall 26-792. Exact model ZHX-PB22 verified; ZHX-PB23 rejected. Real URL, fetched-at and observed statuses are saved in `docs/evidence/live-cpsc.json`; raw observed API schema is in `services/api/tests/fixtures/cpsc-live.json`. Local live-run envelope is saved separately when verified. CPSC is authoritative public data, not evidence of a paid sponsor integration.

## Official implementation references

- CPSC: https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information
- Gemini SDK: https://googleapis.github.io/python-genai/
- Bright Data MCP: https://github.com/brightdata/brightdata-mcp
- System One catalog guidance: https://docs.system-one.dev/en/docs/models

No claims were submitted or messages sent. Only the explicitly approved existing GitHub branch push and DigitalOcean deployment were published.

## Verified settlement branch

**PROVEN locally and on the public deployment with live primary reads:** Kirkbride et al. v. The Kroger Co., case 2:21-cv-00022. Administrator homepage and document index link the long notice and amended court order. `docs/evidence/p1-settlement-live.json` records all four URLs, timestamps, hashes and passages. Live browser verifies deadline/uncertainty/local approval/export. Preparation-only: insurance, geography, qualifying transaction, exclusions and proof remain unconfirmed; no real claim or payment asserted.

**P1 remains incomplete:** Bright Data scrape remains unproven (calls stopped per user). DigitalOcean public deployment/health and live-source browser workflows now proven. No P2 work started.
