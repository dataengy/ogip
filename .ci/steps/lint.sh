#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
log "ruff check + format (incl. the nested dagster project — #39)"
uv run ruff check . experimental/orchestration/dagster_ogip/src
uv run ruff format --check . experimental/orchestration/dagster_ogip/src
log "SQL lint"
bash .ci/steps/sql-lint.sh
