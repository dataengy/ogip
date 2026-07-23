#!/usr/bin/env bash
# Local drift gate for the ingestion source registry — pre-commit half.
#
# The registry SSoT lives OUTSIDE this repo (~/.ai/skills — per-source YAMLs, routing
# rules) and spec/sources/ here is its generated projection. CI runners don't have ~/.ai,
# so CI cannot check this; a local prek hook is the only honest placement. Three gates:
#   split-check      — registry files well-formed (incl. required provenance)
#   route-all        — recorded engine vs rulebook: ⚠️ DRIFT exits 1
#   spec-emit-check  — spec/sources/games/ projections not stale vs the registry
#
# Skip-if-absent BY DESIGN: a clone without ~/.ai (CI, another machine) exits 0 silently —
# this gate protects the registry's editors, not every contributor.
set -euo pipefail

JF="${HOME}/.ai/skills/_scripts/de/ingestion/Justfile"
if [[ ! -f "$JF" ]] || ! command -v just >/dev/null 2>&1; then
  exit 0 # no registry on this machine — nothing to guard
fi

repo_root="$(git rev-parse --show-toplevel)"

# prek runs hooks in a sanitized env whose bare python3 lacks pyyaml — pin the registry
# scripts' interpreter to this project's venv (has pyyaml via dlt) instead of trusting PATH.
INGESTION_PY="env UV_PROJECT_ENVIRONMENT=${repo_root}/.run/venv uv run --project ${repo_root} python"
export INGESTION_PY

just -f "$JF" split-check
just -f "$JF" route-all
cd "$repo_root" && just -f "$JF" spec-emit-check . games
