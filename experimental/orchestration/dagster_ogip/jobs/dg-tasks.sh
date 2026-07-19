#!/usr/bin/env bash
# One dispatch script for the Dagster op-jobs — the deterministic side of the definitions.
# The definitions module (defs/orchestration/) only wires ops/schedules/sensors to these tasks,
# so all shell logic lives here (testable in isolation, one place to change).
#
#   jobs/dg-tasks.sh <task>
#     build-dwh            full pipeline, INCREMENTAL dbt run (raw ensured → dbt build)
#     build-dwh-full       full pipeline, FULL-REFRESH dbt run (raw ensured → dbt build --full-refresh)
#     update-dbt           regenerate the dbt project from spec/ + parse (no run)
#     update-dbt-changed   regenerate + run only models changed vs the last manifest (state:modified+)
#     parsing              run the scraper/parser → Postgres landing (placeholder: ingestion lane P1)
#     prefect              trigger the root Prefect flow (the alt orchestrator)
#     cdc [--stream|--dry-run]   ingestr CDC from the Postgres landing zone (delegates to cdc/)
set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$PROJECT" && git rev-parse --show-toplevel)"
cd "$PROJECT"
# shellcheck source=jobs/dbt-env.sh
source "$PROJECT/jobs/dbt-env.sh" # SSoT: DBT_PROJECT_DIR

task="${1:?usage: dg-tasks.sh <build-dwh|dbt-evaluate|dbt-deps|build-dwh-full|update-dbt|update-dbt-changed|parsing|prefect|cdc>}"

# dbt wants --project-dir/--profiles-dir AFTER the subcommand, so append them via a helper
# rather than a prefix array.
dbt_run() { uv run dbt "$@" --project-dir "$DBT_PROJECT_DIR" --profiles-dir "$DBT_PROJECT_DIR"; }

# spec/ (Bruin) is the SSoT — the dbt project is generated, never hand-authored (ADR-0005/0015).
compile_dbt() {
  PYTHONPATH="$REPO/src" .venv/bin/python - "$REPO" "$DBT_PROJECT_DIR" <<'PY'
import sys
from pathlib import Path

from ogip.spec_compile.to_dbt import compile_to_dbt

root = Path(sys.argv[1]).resolve()
compile_to_dbt(
    root / "spec" / "sql", Path(sys.argv[2]),
    warehouse=root / ".run" / "data" / "warehouse" / "ogip.duckdb", repo_root=root,
)
print("dbt project regenerated from spec/")
PY
}

ensure_raw() {
  mkdir -p "$REPO/.run/data/warehouse"
  if ! ls "$REPO"/.run/data/raw/rawg__games/*.parquet >/dev/null 2>&1; then
    echo "[dg-tasks] raw absent — running dlt ingestion first"
    uv run dg launch --assets 'key:"raw/rawg__games"'
  fi
}

# Install the dbt-hub packages once (packages.yml is emitted by the compiler). Idempotent —
# dbt caches into dbt/dbt_packages/, so skip when already present.
ensure_deps() {
  [[ -d "$DBT_PROJECT_DIR/dbt_packages" ]] || dbt_run deps
}

case "$task" in
  build-dwh)
    compile_dbt
    ensure_deps
    ensure_raw
    dbt_run build
    ;;
  build-dwh-full)
    compile_dbt
    ensure_deps
    ensure_raw
    dbt_run build --full-refresh
    ;;
  dbt-evaluate)
    # Use a package: dbt_project_evaluator audits the project for modeling/testing/docs issues.
    compile_dbt
    ensure_deps
    ensure_raw
    dbt_run build --select package:dbt_project_evaluator
    ;;
  dbt-deps)
    compile_dbt
    dbt_run deps
    ;;
  update-dbt)
    compile_dbt
    ensure_deps
    dbt_run parse
    ;;
  update-dbt-changed)
    compile_dbt
    # state:modified needs a prior manifest; fall back to a full build on the first run.
    if [[ -f "$DBT_PROJECT_DIR/target/manifest.json" ]]; then
      cp "$DBT_PROJECT_DIR/target/manifest.json" "$DBT_PROJECT_DIR/.prev_manifest.json"
      dbt_run build --select 'state:modified+' --state "$DBT_PROJECT_DIR" || dbt_run build
    else
      dbt_run build
    fi
    ;;
  parsing)
    echo "[dg-tasks] parsing: scraper → Postgres landing is the ingestion lane's P1 (async ScraperSource, ADR-0014)."
    echo "[dg-tasks] placeholder no-op — wire ingestion/sources/*scraper* here when it lands."
    ;;
  prefect)
    if [[ -f "$REPO/pipelines/flows/main.py" ]]; then
      echo "[dg-tasks] triggering the root Prefect flow (alt orchestrator)"
      (cd "$REPO" && UV_PROJECT_ENVIRONMENT=.run/venv uv run python -m pipelines.flows.main)
    else
      echo "[dg-tasks] pipelines/flows/main.py absent — Prefect lane not present in this checkout."
    fi
    ;;
  cdc)
    bash "$PROJECT/cdc/ingestr_cdc.sh" "${@:2}"
    ;;
  *)
    echo "[dg-tasks] unknown task: $task" >&2
    exit 2
    ;;
esac
