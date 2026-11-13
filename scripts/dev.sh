#!/usr/bin/env bash
set -euo pipefail
api_pid=
web_pid=
cleanup() {
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
  if [[ -n "$web_pid" ]]; then kill "$web_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM
services/api/.venv/bin/uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000 &
api_pid=$!
pnpm --dir apps/web dev --port "${WEB_PORT:-3000}" &
web_pid=$!
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done
printf '%s\n' 'One app stopped. Closing its companion process.' >&2
exit 1
