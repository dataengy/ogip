# Task — ML feature tasks + separated per-engine Prefect setups + Dagster-from-Prefect

**Status:** 🟢 shipped — every SQL-tool setup has its own Prefect flow, runs the ML feature step,
and is covered by e2e; `log` is the house logger alias; Makefile is the pipeline launcher.

## Delivered

- **ML feature-engineering tasks** (`experimental/python_tasks/tasks.py`): standardize, min-max,
  outlier winsorizing, interactions, quantile bucketing, one-hot (+top-n), release-year cohort
  features, deterministic leakage-safe train/test split, feature-matrix assembler — all pure.
- **Typed boundary** (`experimental/python_tasks/pipeline.py`): `build_ml_features(warehouse,
  outputs_dir) -> dict[str, int]` reads `core.game`, runs the tasks, writes
  `ml_features/ml_train/ml_test.parquet`. Dataframes never cross into pyright-strict code.
- **Separated per-engine Prefect setups** (`pipelines/flows/engines/`): one flow module per SQL
  tool — `prefect_{sqlmesh,sql,dbt,opendbt,sqlmesh_dbt,bruin}.py` — each a self-contained setup
  with `@materialize` assets (engine-namespaced lineage), sharing step logic via `_common.py`
  (`make_engine_flow`). Every setup runs ingest → transform → **ML** → publish.
- **Dagster-from-Prefect** (`prefect_dagster.py`, profile `prefect-over-dagster`): Dagster owns
  dlt+dbt (`dg launch`), Prefect owns ML + publish + alerting. Skill: `dagster-from-prefect`.
- **Registry + dispatch**: `engines/__init__.py:ENGINE_FLOWS`; `run-profile.py` launches the
  per-engine flow; `main.py` re-exports the SQLMesh flow as `ingest_transform_publish` (back-compat).
- **E2E** (`src/tests/e2e/test_all_setups.py`): base engines always; heavy engines + Dagster behind
  `OGIP_E2E_ALL_ENGINES=1`. Verified: plain_sql + sqlmesh build + produce ML end-to-end.
- **`log` alias**: `ogip.logger` exports `log` (the house alias); all 16 modules migrated
  `logger` → `log`. Convention documented (AGENTS.md, skill `use-log-alias`, project memory).
- **Runner fix**: the plain-SQL runner now drops a mismatched-type object (SQLMesh view vs table)
  before rebuild — comparison engines share one warehouse.

## Verified

`make check` green (ruff, pyright strict 0, pytest). Base-engine e2e green. ML boundary tested
against the real RAWG fixture (5-row matrix, 8 features + label).
