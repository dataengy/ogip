#!/usr/bin/env bash
# One dispatch script for the Dagster op-jobs — the deterministic side of the definitions.
# The definitions module (defs/orchestration/) only wires ops/schedules/sensors to these tasks,
# so all shell logic lives here (testable in isolation, one place to change).
#
#   jobs/dg-tasks.sh <task>
#     build-dwh            regenerate dbt from spec/ + INCREMENTAL dbt build (raw NOT ensured —
#                           the Dagster asset graph expresses raw → dbt, not this task)
#     build-dwh-full       regenerate dbt from spec/ + FULL-REFRESH dbt build (raw NOT ensured)
#     dbt-evaluate         regenerate + run package:dbt_project_evaluator
#     dbt-deps             regenerate + unconditional `dbt deps`
#     update-dbt            regenerate the dbt project from spec/ + parse (no run)
#     update-dbt-changed   regenerate + run models selected by state:modified+ (--state passed
#                           straight through; no manifest-copy fallback)
#     parsing              run the scraper/parser → Postgres landing (placeholder: ingestion lane P1)
#     prefect              trigger the root Prefect flow (the alt orchestrator)
#     cdc [--stream|--dry-run]   ingestr CDC from the Postgres landing zone (delegates to cdc/)
set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$PROJECT" && git rev-parse --show-toplevel)"
cd "$REPO"

task="${1:?usage: dg-tasks.sh <build-dwh|build-dwh-full|dbt-evaluate|dbt-deps|update-dbt|update-dbt-changed|parsing|prefect|cdc>}"

# Every task is a thin alias for a registry call. The bodies live in `src/ogip/tasks/` so the
# Prefect lane runs the SAME code — see docs/superpowers/specs/2026-07-20-odos-*.md §2 for the
# drift this replaces.
ogip_task() { UV_PROJECT_ENVIRONMENT=.run/venv uv run python -m ogip.tasks "$@"; }

# `cdc_flag` runs inside a `$(...)` subshell (see the `cdc)` branch below), so a plain `exit`
# there only ends that subshell — the script would keep going with an empty substitution. Trap
# our own SIGTERM so signalling ourselves from inside the subshell actually aborts the script
# with exit 2; this is the standard escape hatch for "exit the parent from inside $(...)".
trap 'exit 2' TERM

# Map cdc's optional second positional arg to the matching registry flag; "" (no arg) expands
# to zero words downstream, so the `cdc)` branch stays the single-line `ogip_task cdc.catchup
# $(cdc_flag "${2:-}")` shape (unquoted on purpose — see the call site).
cdc_flag() {
  case "$1" in
    "")          ;;
    --dry-run)   echo "--dry_run=true" ;;
    --stream)    echo "--stream=true" ;;
    *)
      echo "[dg-tasks] cdc: unknown flag '$1' (expected --dry-run or --stream)" >&2
      kill -s TERM "$$"
      exit 2
      ;;
  esac
}

DBT_PROJECT="experimental/orchestration/dagster_ogip/dbt"

case "$task" in
  build-dwh)          ogip_task dbt.build --project_dir="$DBT_PROJECT" ;;
  build-dwh-full)     ogip_task dbt.build --project_dir="$DBT_PROJECT" --full_refresh=true ;;
  dbt-evaluate)       ogip_task dbt.build --project_dir="$DBT_PROJECT" --select=package:dbt_project_evaluator ;;
  update-dbt-changed) ogip_task dbt.build --project_dir="$DBT_PROJECT" --select=state:modified+ --state="$DBT_PROJECT" ;;
  dbt-deps)           ogip_task dbt.deps  --project_dir="$DBT_PROJECT" --force=true ;;
  update-dbt)         ogip_task dbt.parse --project_dir="$DBT_PROJECT" ;;
  parsing)            ogip_task ingest.parse_to_landing ;;
  prefect)            ogip_task integrations.trigger_prefect ;;
  cdc)                ogip_task cdc.catchup $(cdc_flag "${2:-}") ;;
  *)
    echo "[dg-tasks] unknown task: $task" >&2
    exit 2
    ;;
esac
