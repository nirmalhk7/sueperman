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
RUN uv sync --project services/api --locked --no-dev --no-cache
COPY services/api/app services/api/app
COPY demo demo
RUN useradd --uid 10001 --create-home sueperman \
    && mkdir -p /data /srv/app/uploads && chown -R 10001:10001 /data /srv/app/uploads
USER 10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--app-dir", "services/api", "--host", "0.0.0.0", "--port", "8080"]
