# Sponsor evidence

Status vocabulary: **PROVEN** requires observed execution and a retrievable local artifact or URL; **PARTIAL** means some implementation/evidence exists but the sponsor's actual live criterion remains unmet; **NOT IMPLEMENTED** means no qualifying integration. Contract tests with doubles are never live proof.

| Category | Status | Evidence and limit |
|---|---|---|
| Best Overall Hack | PROVEN | Local recall discovery, exact-model match, visible excluded near-match, missing-model review, approved-local Markdown download. `docs/evidence/browser-checks.log`, `output/playwright/`. Judge pitch: one purchase history becomes a source-backed remedy checklist. No prize outcome implied. |
| Gemini API | PARTIAL | Official google-genai SDK wired for PNG/JPEG/PDF; real SDK HTTP boundary tested in `test_optional_providers.py`, upload integration in `test_workflow.py`. No live key or authenticated invocation. Identifiers remain unverified suggestions. |
| Bright Data | PARTIAL | MCP stdio adapter calls `search_engine` then `scrape_as_markdown` only for supported official manufacturer page. Source/redirect/injection/error tests pass. Token is now configured; no actual Bright Data request is claimed in this change. |
| System One Models | NOT IMPLEMENTED | Current user choice implements the System 1 decision role using OpenAI, not the System One vendor. Legacy contract tests/catalog remain historical evidence only. OpenAI adapter is tested; live OpenAI proof awaits its key. No System One sponsor claim. |
| DigitalOcean | NOT IMPLEMENTED | No token or doctl available. No deployed service or public deployment health check exists. |
| Sentry Raffle | PROVEN | Real running-app backend and browser errors received: SUEPERMAN-SERVER-1 and SUEPERMAN-FRONTEND-2. Traces, logs, stored masked replay and readable application frames verified. Evidence and URLs: docs/sentry-setup.md. Local proof; production not deployed. |
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

No claims were submitted, messages sent, sponsor accounts created, or external content published.
