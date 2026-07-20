#!/usr/bin/env bash
# E2E — the `dagster-dlt-dbt` combo profile: SOURCE → FINAL LAYER in ONE orchestrated run.
#
#   orchestrator = Dagster · ingestion = dlt · transform = dbt · dq = dbt tests (part of `build`)
#
# One e2e per orchestr+transform+dq combo (A12). This one drives the whole pipeline through
# Dagster's `dg launch` and asserts the FS layer (`fs.market_features`) actually materialized —
# not that a task "ran". Runs headless, no Docker: RAWG demo fixture, DuckDB warehouse. The
# ingestr CDC asset is deliberately excluded (needs a live Postgres, verified separately).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(dirname "$HERE")" # .../dagster_ogip
REPO="$(cd "$PROJECT" && git rev-parse --show-toplevel)"
cd "$PROJECT"
# shellcheck source=jobs/dbt-env.sh
source "$PROJECT/jobs/dbt-env.sh" # SSoT: DBT_PROJECT_DIR

log() { echo "[e2e:dagster-dlt-dbt] $*"; }

# 0. clean slate so the run proves itself, not a leftover warehouse.
rm -rf "$REPO/.run/data/raw" "$REPO/.run/data/warehouse" "$HOME/.dlt/pipelines/rawg" "$DBT_PROJECT_DIR"
mkdir -p "$REPO/.run/data/warehouse" # DuckDB opens, but does not create, the parent dir

# 1. compile spec/ (Bruin, the SSoT) → the dbt project. Never hand-authored (ADR-0005).
log "compile spec → dbt project"
PYTHONPATH="$REPO/src" .venv/bin/python - "$REPO" "$DBT_PROJECT_DIR" <<'PY'
import sys
from pathlib import Path

from ogip.spec_compile.to_dbt import compile_to_dbt

root = Path(sys.argv[1]).resolve()
compile_to_dbt(
    root / "spec" / "sql",
    Path(sys.argv[2]),
    warehouse=root / ".run" / "data" / "warehouse" / "ogip.duckdb",
    repo_root=root,
)
print("compiled")
PY

# 2. SOURCE → raw Parquet: materialize the dlt RAWG asset (Layer 0).
log "dg launch — dlt ingestion (source → raw Parquet)"
uv run dg launch --assets 'key:"raw/rawg__games"'

# 3. TRANSFORM + DQ: `dbt build` runs models AND the generated tests, in one Dagster run.
log "dg launch — dbt build (transform + dq) → FS layer"
uv run dg launch --assets 'key:"rawg__games"+'

# 4. ASSERT the FINAL layer materialized with real rows and satisfies the feature contract.
log "assert fs.market_features"
uv run python - "$REPO" <<'PY'
import sys
from pathlib import Path

import duckdb

wh = str(Path(sys.argv[1]) / ".run" / "data" / "warehouse" / "ogip.duckdb")
con = duckdb.connect(wh, read_only=True)
rows = con.execute("select count(*) from fs.market_features").fetchone()[0]
nulls = con.execute(
    "select count(*) from fs.market_features where popularity_score is null"
).fetchone()[0]
assert rows > 0, "fs.market_features is empty — pipeline produced no final layer"
assert nulls == 0, "popularity_score has nulls — feature contract violated"
print(f"OK fs.market_features rows={rows} popularity_score nulls={nulls}")
PY

log "PASS — dagster-dlt-dbt combo: source → FS layer green"
