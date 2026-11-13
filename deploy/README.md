# App Platform deployment

`app-spec.json` targets the existing `nirmalhk7/sueperman` repository and `codex/sueperman` branch. It uses the public Git clone source rather than GitHub OAuth, which is not connected in this account. It defines one API instance and one web instance, with `/api` preserved by ingress. The deployment is a shared hackathon demo, not private account storage. SQLite state is ephemeral on App Platform and can disappear on redeploy; keep durable personal records outside this demo. No Postgres/P2 dependency was added.

The web image builds with an explicitly empty `NEXT_PUBLIC_API_BASE_URL`, making browser requests same-origin `/api` rather than the visitor's localhost. Bindable App Platform URLs are only used at runtime for backend origin checks. The container build labels shared data and tells visitors to use synthetic purchases.

Run `make container-test` with Docker/OrbStack running. It builds Linux AMD64 images (App Platform's supported architecture), starts an isolated API/web/proxy project on `127.0.0.1:3080`, checks health and fixture matching, approves/exports a local draft, verifies non-root app users and absence of private env files, and runs the core browser workflow against the production build. It cleans only its own containers/network/SQLite volume. All live providers are disabled for this test; no model credits are consumed. Set `CONTAINER_WEB_PORT` if 3080 is occupied.

The local proxy exists only to reproduce App Platform ingress; the cloud app has two services, not three. `.dockerignore` excludes env files, credentials, local databases, uploads and recordings. Backend Node/npm support the optional Bright Data MCP adapter; no provider credential enters an image.

Before creating an app, POST `{"spec": <app-spec.json>}` to DigitalOcean's `/v2/apps/propose`. A real proposal was accepted with base app cost 10 USD/month for the two selected instances; see `../docs/evidence/p1-digitalocean-proposal.json`. Proposal does not create an app. The operator token stays in ignored root `.env` as `DIGITALOCEAN_ACCESS_TOKEN`; never copy it to application environment variables or source. App creation must use a branch containing these Dockerfiles. Source publication must be authorized before pushing it.

OpenAI receipt-photo reading is the sole paid feature enabled in the current public spec, with a 10-attempt shared daily cap. Investigation routing, Gemini and Bright Data remain off. Only configure backend provider keys as runtime secrets and enable those flags deliberately. CPSC and reviewed settlement public reads are enabled. Gemini's model override reflects this account's verified available model; the retired 2.5 default was rejected for this account. Optional frontend Sentry DSN is a build argument; backend DSN is a runtime setting. No Sentry auth token is baked into images.

After an actual deployment, verify the deployment reaches ACTIVE, request the public `/api/health` and `/`, then run the core browser workflow using that public URL. Do not mark DigitalOcean PROVEN from local containers or a successful proposal alone.

Official references:

- [App specification](https://docs.digitalocean.com/products/app-platform/reference/app-spec/)
- [Proposal/validation endpoint](https://docs.digitalocean.com/reference/pydo/reference/apps/validate_app_spec/)
- [Docker build arguments and runtime bindable variables](https://docs.digitalocean.com/support/why-cant-i-access-my-environment-variables-at-build-time-when-building-from-a-dockerfile-on-app-platform/)
- [AMD64 requirement](https://docs.digitalocean.com/products/app-platform/how-to/deploy-from-container-images/)
- [Pricing](https://docs.digitalocean.com/products/app-platform/details/pricing/)

Observed deployment: app `044b649f-018f-4062-bd9a-195919becfb3`, deployment `ac96b96b-f2f5-49f9-a808-971f110322b4`, source commit `4aee3c3`, ACTIVE. [Public shared demo](https://sueperman-6t4xk.ondigitalocean.app). Public health/home HTTP 200, fixture browser and both live CPSC/settlement browser draft workflows passed. The initial GitHub-source request returned `GitHub user not authenticated`; the documented public Git source succeeded without changing repository privacy or authorizing OAuth. Provider keys were never sent to App Platform. Sentry production delivery remains unverified.

Receipt-camera update: the spec enables only OpenAI receipt-photo reading, capped at 10 attempted calls per UTC day across the shared database. Configure `OPENAI_API_KEY` as an API-service `RUN_TIME` `SECRET`; never put its value in this file or the checked-in spec. Keep OpenAI investigation routing, Gemini and Bright Data flags off unless deliberately enabled. The quota is atomic/persisted across process restarts, but ephemeral App Platform SQLite resets on redeploy; it is not a provider-side monetary budget. Public deployment verification must check `openai_receipts` configured/enabled and one synthetic camera upload before claiming photo OCR works publicly.

Observed camera deployment: commit `f8ff31f`, deployment `401a7c82-185e-4d90-8747-2555e44d5321`, ACTIVE. Public camera upload and cached duplicate succeeded; receipt provider health is enabled/configured. Runtime API key remains an API-only encrypted secret. Earlier public request failures are retained with no invented cause; current actual proof is `../docs/evidence/receipt-camera-public.json`.
