# Known limitations

- Local P0 application; no authentication, no public deployment. DigitalOcean credentials and `doctl` are unavailable. No deployment success claimed.
- Live CPSC supported normalizer is intentionally limited to official notice 26-792. Its exact affected-product description is checked; unfamiliar restrictions require manual review. Other recalls are discovered but cannot become verified positives without a tested normalizer. Catalog coverage is not comprehensive.
- Bright Data/Gemini integrations and the OpenAI System 1 decision role are flag-gated and covered at external transport boundaries. OpenAI/Gemini keys remain absent. A Bright Data key has since been configured, but no new live Bright Data result is claimed in this Sentry/OpenAI change. The former System One vendor adapter is retained only for compatibility; orchestration now selects OpenAI.
- Gemini identifiers from images/PDFs are suggestions, not verified facts. There is no in-app identifier editing flow; import a user-confirmed CSV. No live image/PDF extraction proof recorded.
- No genuine administrator/court cross-verified open settlement is implemented. The only settlement is explicitly fictional. Its deterministic replay evaluates as of 2026-11-13; it never represents a currently available real claim or payout.
- Sentry local errors, traces, logs, masked replay and readable application frames are proven in docs/sentry-setup.md. No production deployment or production source-map upload is claimed; a build-time upload credential and deployed verification remain necessary.
- No HyperFrames output, Tiger Data connection, Snowflake Cortex query, scheduler or Devpost submission. P2 deferred; no externally posted artifacts.
- SQLite and in-process BackgroundTasks suit a local demo. Runs are bounded to 90 seconds; backend restarts mark unfinished runs partial. Product processing is sequential for deterministic database/event order; external providers are bounded and cached. No distributed or durable worker guarantee.
- Source policy checks exact HTTPS hosts, public DNS addresses and redirects for supported manufacturer URLs. URLs are not supplied by users. This is not a general-purpose arbitrary-web researcher.
- Ready-for-review describes the draft, not complete evidence or formal eligibility. Required model/serial photos and disposal confirmation remain missing until user supplies them independently. No declarations or external submissions exist.
- Browser verification used port 3001 because unrelated career-ops occupied 3000. Clean-clone Make defaults remain 3000; both apps were started with `make dev WEB_PORT=3001`.
- Browser acceptance recording is an automated walkthrough, not a narrated 90-second judge video. The exact 90-second live presentation script is in DEMO.md.
- One upstream Starlette TestClient deprecation warning remains visible in test output. It is not a failing check.
