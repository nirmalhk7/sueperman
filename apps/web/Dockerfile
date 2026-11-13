FROM node:24-bookworm-slim AS build
RUN npm install --global pnpm@11.25.0
WORKDIR /srv/app/apps/web
COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
# Empty means same-origin /api, independent of the eventual public hostname.
ARG NEXT_PUBLIC_API_BASE_URL=""
ARG NEXT_PUBLIC_SENTRY_DSN=""
ARG NEXT_PUBLIC_SHARED_DEMO="true"
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN \
    NEXT_PUBLIC_SHARED_DEMO=$NEXT_PUBLIC_SHARED_DEMO NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:24-bookworm-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /srv/app/apps/web
COPY --from=build --chown=node:node /srv/app/apps/web ./
USER node
EXPOSE 8080
CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0", "--port", "8080"]
