# OGIP — main developer commands (thin wrappers). Heavy/spec ops live in the Justfile.
.DEFAULT_GOAL := help
SHELL := /bin/bash

# Runtime lives under .run/ (venv, caches, data zones, artifacts)
export UV_PROJECT_ENVIRONMENT := .run/venv

COMPOSE := docker compose -f deploy/docker-compose.yml --env-file .env
# Obs stack is a standalone compose file (lane `obs`), not a --profile of the base one:
# deploy/docker-compose.yml is owned by other lanes. See deploy/obs/README.md.
OBS := docker compose -f deploy/obs/docker-compose.obs.yml --env-file .env
PREK := uvx prek --config config/.pre-commit-config.yaml

.PHONY: help bootstrap render-env lint fmt typecheck sql-lint \
        test test-smoke test-unit test-integration test-e2e check ci hooks clean \
        up down ps logs obs-up obs-down storage-up storage-down run notebook

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Install deps (uv → .run/venv), pre-commit (prek) hooks, render .env
	uv sync
	$(PREK) install
	uv run python config/.env-render.py

.env: config/config.yml config/.env-render.py ## (auto) render .env from SSoT
	uv run python config/.env-render.py

render-env: ## Re-render .env from config/config.yml (merge-safe on secrets)
	uv run python config/.env-render.py

# --- Quality gates ---
lint: ## Ruff lint + format check + SQL lint
	uv run ruff check .
	uv run ruff format --check .
	@$(MAKE) sql-lint

fmt: ## Auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Pyright strict
	uv run pyright

sql-lint: ## Lint portable SQL (Bruin @bruin headers stripped) via sqlfluff
	@bash .ci/steps/sql-lint.sh

test: ## Fast tests: smoke + unit (integration + e2e excluded)
	uv run pytest -m "not integration and not e2e"

test-smoke: ## Smoke: cheap wiring (config renders, imports)
	uv run pytest -m smoke

test-unit: ## Unit tests (no external services)
	uv run pytest -m "not smoke and not integration and not e2e"

test-integration: ## Integration tests (need services from 'make up')
	uv run pytest -m integration

test-e2e: ## E2E: run the Prefect job end-to-end and assert results
	uv run pytest -m e2e

check: lint typecheck test ## All quality gates (CI parity)

ci: ## Run the shared CI steps exactly as GitHub Actions runs them
	bash .ci/run.sh lint
	bash .ci/run.sh typecheck
	bash .ci/run.sh test

hooks: ## Run all pre-commit hooks over the whole tree
	$(PREK) run --all-files

clean: ## Remove caches/artifacts (keeps .run/venv and data)
	rm -rf .run/pytest_cache .run/ruff_cache .run/.coverage .run/junit.xml dist
	find . -type d -name __pycache__ -not -path './.run/*' -prune -exec rm -rf {} +

# --- Infrastructure ---
up: .env ## Start core services (Postgres, Prefect) and wait for health
	$(COMPOSE) up -d --wait postgres prefect
	@echo "Prefect UI: http://localhost:4200"
	open http://localhost:4200

down: ## Stop services (volumes preserved)
	$(COMPOSE) down

ps: ## Service status
	$(COMPOSE) ps

logs: ## Tail service logs
	$(COMPOSE) logs -f --tail=100

obs-up: .env ## Start observability stack (VictoriaMetrics, Loki, Alloy, Grafana)
	@mkdir -p .run/logs   # Alloy bind-mounts this; docker would otherwise create it as root
	$(OBS) up -d --wait
	@just obs-verify

obs-down: ## Stop observability stack (volumes preserved)
	$(OBS) down

# --- Object storage (D2 / ADR-0003): the `minio` lake profile ---
# `make down` still stops these — compose removes every container in the project.
storage-up: .env ## Start MinIO (S3-compatible lake) + create the raw bucket
	$(COMPOSE) --profile storage up -d --wait minio
	$(COMPOSE) --profile storage run --rm minio-init
	@echo "MinIO console: http://localhost:$${MINIO_CONSOLE_PORT:-9001} — dev keys ogipminio / ogipminio123"
	@echo "Use it:  set storage.backend=minio in config/config.yml → make render-env"

storage-down: ## Stop MinIO (data volume preserved)
	$(COMPOSE) --profile storage stop minio

# --- Pipeline (default profile: prefect-sqlmesh) ---
run: .env ## Run the pipeline on sample data (default run-profile)
	@just run-profile prefect-sqlmesh

notebook: ## Open JupyterLab on the ML-ready datasets
	uv run jupyter lab --notebook-dir notebooks
