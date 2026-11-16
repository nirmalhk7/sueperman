FROM node:24-bookworm-slim AS node-runtime
FROM ghcr.io/astral-sh/uv:0.10.8 AS uv-runtime
FROM python:3.12-slim-bookworm
COPY --from=uv-runtime /uv /usr/local/bin/uv
# Optional Bright Data MCP uses Node/npm; no credentials enter the build.
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PYTHON_DOWNLOADS=never \
    PATH=/srv/app/services/api/.venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
    DATABASE_URL=sqlite:////data/sueperman.db
WORKDIR /srv/app
COPY services/api/pyproject.toml services/api/uv.lock services/api/
ARG CONTAINER_OFFLINE_WHEELS=0
RUN --mount=type=bind,source=services/api/container-wheels,target=/wheels,readonly \
    if [ "$CONTAINER_OFFLINE_WHEELS" = "1" ]; then \
      sha256sum -c /wheels/LOCK.sha256 && uv venv services/api/.venv && \
      uv pip install --python services/api/.venv/bin/python --offline --no-index \
        --find-links=/wheels --require-hashes -r /wheels/requirements.txt; \
    else uv sync --project services/api --locked --no-dev --no-cache; fi
COPY services/api/app services/api/app
COPY demo demo
# Cloud checkouts may have mode 0600/0700. Public code stays root-owned and
# becomes readable/traversable by the non-root runtime, never writable by it.
RUN chmod -R a+rX /srv/app/services/api/app /srv/app/demo \
    && useradd --uid 10001 --create-home sueperman \
    && mkdir -p /data /srv/app/uploads && chown -R 10001:10001 /data /srv/app/uploads
USER 10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--app-dir", "services/api", "--host", "0.0.0.0", "--port", "8080"]
