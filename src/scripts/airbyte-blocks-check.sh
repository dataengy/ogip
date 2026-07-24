#!/usr/bin/env bash
# Local gate for the `airbyte:` blocks in the ingestion source registry — pre-commit half.
#
# The registry SSoT lives OUTSIDE this repo (~/.ai/skills); spec/sources/ here is its
# generated projection. Every airbyte: block must be internally valid and externally real:
#   - the connector EXISTS in the live OSS registry (source-twitch was a fiction);
#   - sync_mode=incremental carries a cursor;
#   - streams is non-empty.
# This fires only when spec/sources/ or the Airbyte lane is touched, and self-skips on any
# machine without ~/.ai (CI, another clone) — it protects the registry's editors, mirroring
# src/scripts/sources-registry-check.sh.
set -euo pipefail

JF="${HOME}/.ai/skills/_scripts/de/ingestion/Justfile"
if [[ ! -f "$JF" ]] || ! command -v just >/dev/null 2>&1; then
  exit 0 # no registry on this machine — nothing to guard
fi

repo_root="$(git rev-parse --show-toplevel)"

# prek's sanitized python3 lacks pyyaml — pin the registry script's interpreter to this
# project's venv (pyyaml via dlt), exactly as sources-registry-check.sh does.
# The Justfile reads its interpreter from env: PY := env_var_or_default("INGESTION_PY", "python3").
INGESTION_PY="env UV_PROJECT_ENVIRONMENT=${repo_root}/.run/venv uv run --project ${repo_root} python"
export INGESTION_PY
just -f "$JF" airbyte-validate
