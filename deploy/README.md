# App Platform deployment

`app-spec.json` targets the existing `nirmalhk7/sueperman` repository and `codex/sueperman` branch. It defines one API instance and one web instance, with `/api` preserved by ingress. The deployment is a shared hackathon demo, not private account storage. SQLite state is ephemeral on App Platform and can disappear on redeploy; keep durable personal records outside this demo. No Postgres/P2 dependency was added.

The web image builds with an explicitly empty `NEXT_PUBLIC_API_BASE_URL`, making browser requests same-origin `/api` rather than the visitor's localhost. Bindable App Platform URLs are only used at runtime for backend origin checks. The container build labels shared data and tells visitors to use synthetic purchases.

Run `make container-test` with Docker/OrbStack running. It builds Linux AMD64 images (App Platform's supported architecture), starts an isolated API/web/proxy project on `127.0.0.1:3080`, checks health and fixture matching, approves/exports a local draft, verifies non-root app users and absence of private env files, and runs the core browser workflow against the production build. It cleans only its own containers/network/SQLite volume. All live providers are disabled for this test; no model credits are consumed. Set `CONTAINER_WEB_PORT` if 3080 is occupied.

The local proxy exists only to reproduce App Platform ingress; the cloud app has two services, not three. `.dockerignore` excludes env files, credentials, local databases, uploads and recordings. Backend Node/npm support the optional Bright Data MCP adapter; no provider credential enters an image.

Before creating an app, POST `{"spec": <app-spec.json>}` to DigitalOcean's `/v2/apps/propose`. A real proposal was accepted with base app cost 10 USD/month for the two selected instances; see `../docs/evidence/p1-digitalocean-proposal.json`. Proposal does not create an app. The operator token stays in ignored root `.env` as `DIGITALOCEAN_ACCESS_TOKEN`; never copy it to application environment variables or source. App creation must use a branch containing these Dockerfiles. Source publication must be authorized before pushing it.

Paid model/research flags default off in the public spec. Only configure backend provider keys as runtime secrets and enable those flags deliberately. CPSC and reviewed settlement public reads are enabled. Gemini's model override reflects this account's verified available model; the retired 2.5 default was rejected for this account. Optional frontend Sentry DSN is a build argument; backend DSN is a runtime setting. No Sentry auth token is baked into images.

After an actual deployment, verify the deployment reaches ACTIVE, request the public `/api/health` and `/`, then run the core browser workflow using that public URL. Do not mark DigitalOcean PROVEN from local containers or a successful proposal alone.

Official references:

- [App specification](https://docs.digitalocean.com/products/app-platform/reference/app-spec/)
- [Proposal/validation endpoint](https://docs.digitalocean.com/reference/pydo/reference/apps/validate_app_spec/)
- [Docker build arguments and runtime bindable variables](https://docs.digitalocean.com/support/why-cant-i-access-my-environment-variables-at-build-time-when-building-from-a-dockerfile-on-app-platform/)
- [AMD64 requirement](https://docs.digitalocean.com/products/app-platform/how-to/deploy-from-container-images/)
- [Pricing](https://docs.digitalocean.com/products/app-platform/details/pricing/)
