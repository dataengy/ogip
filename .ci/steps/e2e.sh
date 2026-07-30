#!/usr/bin/env bash
# E2E — run the Prefect pipeline end-to-end (ephemeral, demo fixture) and assert outputs.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
log "pytest -m e2e (runs the Prefect job)"
uv run pytest -m e2e
log "dq monitors against the warehouse the e2e just built"
uv run python dq/run.py
