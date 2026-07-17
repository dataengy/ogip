# Task — M0: Walking skeleton (RAWG → ML outputs, on Prefect+dlt+SQLMesh)

**Status:** ✅ done — pipeline runs end-to-end; `make check` green; e2e green locally + in CI; CI 7/7.

## Delivered

- **Ingestion (dlt):** `ingestion/base/` (BaseSource/ApiSource/ScraperSource) + `ingestion/sources/rawg.py`.
  Lands raw Parquet `raw/rawg__games/*.parquet` (Layer-0 `<system>__<table>` + `_ingested_at`/`etl_batch_id`).
  Demo mode = synthetic fixture (`ingestion/samples/`, labeled); live = httpx+tenacity → dlt when `RAWG_API_KEY` set.
- **Spec (SSoT):** `spec/contracts/rawg/rawg__games.odcs.yaml` (ODCS) + Bruin-format SQL
  `spec/sql/{raw,staging,core,fs}` (raw view → stg_games → game → market_features).
- **Transform (SQLMesh):** `src/ogip/spec_compile/` (thin Bruin→SQLMesh compiler) + `transform/sqlmesh/config.yaml`
  (DuckDB gateway). `src/ogip/warehouse.py` exports relations → Parquet.
- **Orchestration (Prefect):** `pipelines/flows/main.py` — `ingest_transform_publish` (ephemeral, no Docker).
- **Outputs:** `.run/data/outputs/{games,market_features}.parquet` (5 rows each). Demo notebook `notebooks/01_explore_datasets.ipynb`.
- **Tests:** `src/tests/e2e/test_pipeline.py` runs the Prefect job + asserts outputs (D17). CI `e2e` job added.

## Verified

- Local: `make run` → outputs; `make test-e2e` passes (23s); `make check` green (pyright 0 errors, 6 unit + 1 e2e).
- Remote: pushed to `dataengy/ogip`; CI green 7/7 (lint·typecheck·test·**e2e**·bash-lint·structure-validate·secret-scan).

## Notes / follow-ups

- Docker unavailable in this env → ran Prefect **ephemerally** (the `make up` Postgres/server path is for M1+).
- Loose ends referenced but not yet built (non-blocking): `just capture-sample`, `integrations/prefect/` deploy/trigger,
  `src/scripts/run-profile.py`, Evidence scaffold (`experimental/bi/evidence/`). Build with M1–M4.

## Next → M1–M4

Replicate the RAWG→outputs slice across the alt toolsets (prefect-bruin, prefect-dbt, prefect-sqlmesh-over-dbt,
prefect-dagster-dlt-dbt); add the Evidence visualizer; then broaden (more sources, star/am layers, DQ, observability).
