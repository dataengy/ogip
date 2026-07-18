"""Warehouse layer jobs — building the DWH from raw to the FS layer.

Two families: **asset jobs** select over the dbt/dlt assets (one per layer + the whole DWH);
**op jobs** give explicit full-refresh vs incremental control the asset layer does not. Their
schedules and the raw-data sensors live here too, next to the jobs they drive.
"""

import dagster as dg
from dagster import OpExecutionContext, SensorEvaluationContext
from dagster_ogip._lib.orchestration import (
    K_CORE,
    K_FS,
    K_RAW_DLT,
    K_STAGING,
    WAREHOUSE,
    run_task,
)

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


# ---- schedules ----
schedules = [
    dg.ScheduleDefinition(
        name="daily_dwh_full_refresh",
        job=dwh_full_refresh_job,
        cron_schedule="0 3 * * *",
        description="Nightly (03:00) full rebuild of the whole DWH.",
    ),
    dg.ScheduleDefinition(
        name="hourly_dwh_incremental",
        job=dwh_incremental_job,
        cron_schedule="0 * * * *",
        description="Hourly incremental refresh to keep the FS layer fresh between full rebuilds.",
    ),
    dg.ScheduleDefinition(
        name="daily_raw_ingest",
        job=raw_ingest_job,
        cron_schedule="30 1 * * *",
        description="Daily (01:30) raw ingestion, ahead of the nightly full refresh.",
    ),
]


# ---- sensors that drive warehouse jobs ----
@dg.asset_sensor(
    asset_key=K_RAW_DLT,
    job=dwh_assets_job,
    name="raw_landed_runs_dwh",
    description="When new raw Parquet materializes, rebuild the whole DWH (raw→stg→core→fs).",
)
def raw_landed_sensor(
    context: SensorEvaluationContext, asset_event: dg.EventLogEntry
) -> dg.RunRequest:
    return dg.RunRequest(run_key=str(asset_event.timestamp))


@dg.sensor(
    job=dwh_incremental_job,
    minimum_interval_seconds=60,
    name="new_postgres_raw_data",
    description="Poll the Postgres `landing` schema row count; run the incremental DWH when it "
    "grows. Skips cleanly when no landing DB is configured.",
)
def new_postgres_raw_sensor(context: SensorEvaluationContext) -> dg.SensorResult | dg.SkipReason:
    try:
        import os

        import psycopg

        dsn = os.environ.get("OGIP_PG_DSN")
        if not dsn:
            return dg.SkipReason("OGIP_PG_DSN not set — no landing DB to watch")
        with psycopg.connect(dsn) as conn:
            total = conn.execute(
                "select coalesce(sum(n_live_tup), 0) from pg_stat_user_tables "
                "where schemaname = 'landing'"
            ).fetchone()
        count = str(total[0] if total else 0)
    except Exception as exc:  # sensor must never crash the daemon
        return dg.SkipReason(f"landing DB unavailable ({type(exc).__name__})")
    if context.cursor == count:
        return dg.SkipReason(f"no new landing rows (count={count})")
    return dg.SensorResult(run_requests=[dg.RunRequest(run_key=count)], cursor=count)


# ---- asset check on the FS layer ----
@dg.asset_check(
    asset=K_FS,
    name="market_features_nonempty_and_scored",
    description="FS layer has rows and popularity_score is never null (feature contract).",
    blocking=False,
)
def market_features_check() -> dg.AssetCheckResult:
    if not WAREHOUSE.exists():
        return dg.AssetCheckResult(passed=False, metadata={"reason": "warehouse not built yet"})
    import duckdb

    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    try:
        rows = con.execute("select count(*) from fs.market_features").fetchone()
        nulls = con.execute(
            "select count(*) from fs.market_features where popularity_score is null"
        ).fetchone()
    finally:
        con.close()
    n = int(rows[0]) if rows else 0
    bad = int(nulls[0]) if nulls else 0
    return dg.AssetCheckResult(
        passed=n > 0 and bad == 0, metadata={"rows": n, "null_popularity_score": bad}
    )


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
    schedules=schedules,
    sensors=[raw_landed_sensor, new_postgres_raw_sensor],
    asset_checks=[market_features_check],
)
