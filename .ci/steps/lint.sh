#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
log "ruff check + format"
uv run ruff check .
uv run ruff format --check .
log "SQL lint"
bash .ci/steps/sql-lint.sh
