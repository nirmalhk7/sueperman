# Container trust diagnosis and verified offline build

Normal online `make container-test` failed with `UnknownIssuer` fetching locked Python wheels; Node package installation similarly reported a self-signed certificate chain. Verified HTTPS succeeds on the host. Read-only inspection found the environment proxy CA in host trust but not the unmodified container bundle. No TLS verification, trust store or security setting was changed.

A hash-verified offline input route now passes production container acceptance. On the matching Linux x86_64 trusted host:

```sh
services/api/.venv/bin/python scripts/prepare_container_wheels.py
services/api/.venv/bin/python scripts/prepare_container_web.py
CONTAINER_OFFLINE_WHEELS=1 \
CONTAINER_WEB_DOCKERFILE=apps/web/Dockerfile.offline \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
PLAYWRIGHT_BROWSERS_PATH=/tmp/sueperman-browsers make container-test
```

Wheels are downloaded with locked hashes and installed offline. Web dependencies use the frozen lockfile; archives and relevant inputs are hashed and verified inside a network-disabled build step. Generated dependency archives are ignored and excluded from recovery delivery. Existing host HTTPS trust is used without modification. The normal online route remains blocked by the environment trust mismatch.

The build also corrected source read permissions inside the API image so the nonroot application can read copied source. Root-owned code remains unwritable by that user. The final check passes API behavior, same-origin routing, nonroot/no-env-file checks and four production browser tests (core V1 and all three V2 flows). Log: `container-final.log`.
