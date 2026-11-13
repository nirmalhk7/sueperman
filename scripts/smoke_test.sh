#!/usr/bin/env bash
set -euo pipefail
curl --fail --silent --show-error "${API_URL:-http://localhost:8000}/api/health"
curl --fail --silent --show-error --output /dev/null "${WEB_URL:-http://localhost:3000}"
services/api/.venv/bin/python scripts/seed_demo.py --api "${API_URL:-http://localhost:8000}"
