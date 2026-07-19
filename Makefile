# OGIP — the PIPELINE LAUNCHER. One target per pipeline (1 op = 1 pipeline); every profile in
# config/config.yml → run_profiles has a target here. Every OTHER (small) op lives in the
# Justfile — the catch-all at the bottom forwards `make <op>` to `just <op>`, so `make check`,
# `make up`, `make test`, etc. keep working.
.DEFAULT_GOAL := help
SHELL := /bin/bash
export UV_PROJECT_ENVIRONMENT := .run/venv

.PHONY: help run run-sqlmesh run-sql run-dbt run-opendbt run-sqlmesh-dbt run-bruin \
        run-over-dagster run-dagster-dlt-dbt

help: ## Show the pipelines (all other ops: `just` to list, or `make <op>` → `just <op>`)
	@echo "OGIP pipelines (1 op = 1 pipeline):"
	@grep -E '^run[a-z-]*:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Everything else lives in the Justfile: run 'just' to list, or 'make <op>' forwards to 'just <op>'."

run: run-sqlmesh ## Default pipeline — SQLMesh (production)

run-sqlmesh: ## prefect-sqlmesh (production): dlt → SQLMesh → ML → publish
	@just run-profile prefect-sqlmesh

run-sql: ## prefect-sql: dlt → plain-SQL runner → ML → publish
	@just run-profile prefect-sql

run-dbt: ## prefect-dbt: dlt → generated dbt project → ML → publish
	@just run-profile prefect-dbt

run-opendbt: ## prefect-opendbt: dlt → OpenDBT → ML → publish
	@just run-profile prefect-opendbt

run-sqlmesh-dbt: ## prefect-sqlmesh-over-dbt: dlt → SQLMesh-over-dbt → ML → publish
	@just run-profile prefect-sqlmesh-over-dbt

run-bruin: ## prefect-bruin: dlt → Bruin native → ML → publish
	@just run-profile prefect-bruin

run-over-dagster: ## prefect-over-dagster: Dagster (dlt+dbt) wrapped in Prefect (ML/publish)
	@just run-profile prefect-over-dagster

run-dagster-dlt-dbt: ## prefect-dagster-dlt-dbt: standalone Dagster complete setup
	@just run-profile prefect-dagster-dlt-dbt

# Forward any non-pipeline target to the Justfile (small ops live there). Keeps `make check`,
# `make up`, `make test`, etc. working without duplicating recipe bodies.
Makefile: ;
%:
	@just $@
