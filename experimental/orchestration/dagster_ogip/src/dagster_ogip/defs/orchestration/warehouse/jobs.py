"""Warehouse jobs — building the DWH from raw to the FS layer.

Two families: **asset jobs** select over the dbt/dlt assets (one per EDW layer + the whole DWH);
**op jobs** give the explicit full-refresh vs incremental control the asset layer does not.
Schedules live in `schedules.py`, the driving sensors in `sensors.py`, the FS check in `checks.py`.
"""

import dagster as dg
from dagster import OpExecutionContext
from dagster_ogip._lib.orchestration import K_CORE, K_FS, K_RAW_DLT, K_STAGING, run_task

# ---- asset jobs (idiomatic selection, one per EDW layer + the whole DWH) ----
raw_ingest_job = dg.define_asset_job(
    "raw_ingest_job",
    selection=dg.AssetSelection.assets(K_RAW_DLT),
    description="Layer 0 — land RAWG source data as raw Parquet via dlt (`<system>__<table>`).",
)
staging_job = dg.define_asset_job(
    "staging_job",
    selection=dg.AssetSelection.assets(K_STAGING),
    description="Staging — type/rename/UTC the raw table into stg_games (no business logic).",
)
core_job = dg.define_asset_job(
    "core_job",
    selection=dg.AssetSelection.assets(K_CORE),
    description="Core — the integrated `game` entity (surrogate key) built from staging.",
)
fs_job = dg.define_asset_job(
    "fs_job",
    selection=dg.AssetSelection.assets(K_FS),
    description="Feature Store — market_features (popularity/critic scores), the ML-ready layer.",
)
dwh_assets_job = dg.define_asset_job(
    "dwh_assets_job",
    selection=dg.AssetSelection.assets("rawg__games").downstream(),
    description="Whole DWH — the dbt raw model and everything downstream (raw→stg→core→fs).",
)


# ---- op jobs (explicit full vs incremental dbt runs) ----
@dg.op
def _build_dwh_incremental(context: OpExecutionContext) -> None:
    run_task(context, "build-dwh")


@dg.op
def _build_dwh_full(context: OpExecutionContext) -> None:
    run_task(context, "build-dwh-full")


@dg.job(
    tags={"pipeline": "dwh", "mode": "incremental"},
    description="Incremental DWH build — ensures raw, then `dbt build` (default incremental run). "
    "Cheap enough for the hourly schedule and the new-landing-data sensor.",
)
def dwh_incremental_job() -> None:
    _build_dwh_incremental()


@dg.job(
    tags={"pipeline": "dwh", "mode": "full-refresh"},
    description="Full-refresh DWH build — `dbt build --full-refresh`, rebuilding every model from "
    "scratch. The nightly source of truth; heavier than the incremental run.",
)
def dwh_full_refresh_job() -> None:
    _build_dwh_full()


defs = dg.Definitions(
    jobs=[
        raw_ingest_job,
        staging_job,
        core_job,
        fs_job,
        dwh_assets_job,
        dwh_incremental_job,
        dwh_full_refresh_job,
    ],
)
