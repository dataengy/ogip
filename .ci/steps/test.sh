#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
log "pytest — smoke + unit (integration + e2e excluded)"
uv run pytest -m "not integration and not e2e" --junitxml=.run/junit.xml
