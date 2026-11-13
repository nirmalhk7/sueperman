SHELL := /bin/bash
export UV_CACHE_DIR ?= /tmp/sueperman-uv-cache
export UV_PYTHON_INSTALL_DIR ?= /tmp/sueperman-python
WEB_PORT ?= 3000
API_URL ?= http://localhost:8000
WEB_URL ?= http://localhost:$(WEB_PORT)
export FRONTEND_ORIGIN ?= $(WEB_URL)
export NEXT_PUBLIC_API_BASE_URL ?= $(API_URL)
PY := services/api/.venv/bin/python
.PHONY: setup dev seed test demo lint typecheck smoke e2e build
setup:
	command -v uv
	command -v pnpm
	uv sync --project services/api --python 3.12
	pnpm --dir apps/web install --frozen-lockfile
	pnpm --dir apps/web exec playwright install chromium
dev:
	WEB_PORT=$(WEB_PORT) bash scripts/dev.sh
seed:
	$(PY) scripts/seed_demo.py --seed-only --api $(API_URL)
demo:
	$(PY) scripts/seed_demo.py --api $(API_URL)
test:
	services/api/.venv/bin/pytest services/api/tests -q
	pnpm --dir apps/web test
lint:
	services/api/.venv/bin/ruff check services/api/app services/api/tests scripts
	pnpm --dir apps/web lint
typecheck:
	services/api/.venv/bin/mypy --config-file services/api/pyproject.toml services/api/app
	pnpm --dir apps/web typecheck
smoke:
	API_URL=$(API_URL) WEB_URL=$(WEB_URL) bash scripts/smoke_test.sh
e2e:
	WEB_URL=$(WEB_URL) pnpm --dir apps/web e2e
build:
	pnpm --dir apps/web build
