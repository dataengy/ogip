"""Orchestration entities for the Dagster alt-setup — jobs, schedules, sensors, checks,
partitions. The deterministic shell work lives in `jobs/dg-tasks.sh`; this module only wires
Dagster entities to it and selects over the dbt/dlt/cdc assets defined by the components.

Two families of jobs, on purpose:
- **asset jobs** — idiomatic selection over the dbt/dlt assets (per layer, whole DWH, dlt, cdc).
- **op jobs** — explicit control the asset layer does not give: full vs incremental dbt runs,
  regenerating the dbt subproject, running only changed models, parsing, and Prefect hand-off.
"""

import subprocess
from pathlib import Path

import dagster as dg
from dagster import (
    AssetExecutionContext,
    EventLogEntry,
    OpExecutionContext,
    RunFailureSensorContext,
    SensorEvaluationContext,
)

# .../dagster_ogip/src/dagster_ogip/defs/orchestration/definitions.py
PROJECT = Path(__file__).resolve().parents[4]  # .../dagster_ogip (project root)
REPO = PROJECT.parents[2]  # the git worktree root
TASKS = PROJECT / "jobs" / "dg-tasks.sh"
WAREHOUSE = REPO / ".run" / "data" / "warehouse" / "ogip.duckdb"
SPEC_SQL = REPO / "spec" / "sql"

# Asset keys produced by the components (dlt / dbt / ingestr).
RAW = dg.AssetKey(["raw", "rawg__games"])
DBT_LAYERS = {"raw": "rawg__games", "staging": "stg_games", "core": "game", "fs": "market_features"}


def _run_task(context: OpExecutionContext, *args: str) -> None:
    """Run a `jobs/dg-tasks.sh` task, streaming output into the Dagster run."""
    context.log.info("dg-tasks.sh %s", " ".join(args))
    proc = subprocess.run(["bash", str(TASKS), *args], capture_output=True, text=True, check=False)
    if proc.stdout:
        context.log.info(proc.stdout[-6000:])
    if proc.returncode != 0:
        context.log.error(proc.stderr[-6000:])
        raise dg.Failure(description=f"dg-tasks.sh {' '.join(args)} failed (rc={proc.returncode})")


# --------------------------------------------------------------------------- partitions
daily = dg.DailyPartitionsDefinition(start_date="2026-01-01")


# --------------------------------------------------------------------------- asset jobs
raw_ingest_job = dg.define_asset_job("raw_ingest_job", selection=dg.AssetSelection.assets(RAW))
staging_job = dg.define_asset_job(
    "staging_job", selection=dg.AssetSelection.assets(dg.AssetKey(["staging", "stg_games"]))
)
core_job = dg.define_asset_job(
    "core_job", selection=dg.AssetSelection.assets(dg.AssetKey(["core", "game"]))
)
fs_job = dg.define_asset_job(
    "fs_job", selection=dg.AssetSelection.assets(dg.AssetKey(["fs", "market_features"]))
)
# whole DWH: the dbt raw model + everything downstream (stg → core → fs).
dwh_assets_job = dg.define_asset_job(
    "dwh_assets_job", selection=dg.AssetSelection.assets("rawg__games").downstream()
)
dlt_ingest_job = dg.define_asset_job("dlt_ingest_job", selection=dg.AssetSelection.assets(RAW))
cdc_asset_job = dg.define_asset_job(
    "cdc_asset_job", selection=dg.AssetSelection.assets("cdc_landing")
)


# --------------------------------------------------------------------------- op jobs
@dg.op
def _build_dwh_incremental(context: OpExecutionContext) -> None:
    _run_task(context, "build-dwh")


@dg.op
def _build_dwh_full(context: OpExecutionContext) -> None:
    _run_task(context, "build-dwh-full")


@dg.op
def _update_dbt(context: OpExecutionContext) -> None:
    _run_task(context, "update-dbt")


@dg.op
def _update_dbt_changed(context: OpExecutionContext) -> None:
    _run_task(context, "update-dbt-changed")


@dg.op
def _run_parsing(context: OpExecutionContext) -> None:
    _run_task(context, "parsing")


@dg.op
def _trigger_prefect(context: OpExecutionContext) -> None:
    _run_task(context, "prefect")


@dg.op
def _run_cdc(context: OpExecutionContext) -> None:
    _run_task(context, "cdc", "--dry-run")


@dg.op
def _dbt_evaluate(context: OpExecutionContext) -> None:
    _run_task(context, "dbt-evaluate")


@dg.job(tags={"pipeline": "dwh", "mode": "incremental"})
def dwh_incremental_job() -> None:
    _build_dwh_incremental()


@dg.job(tags={"pipeline": "dwh", "mode": "full-refresh"})
def dwh_full_refresh_job() -> None:
    _build_dwh_full()


@dg.job(tags={"maintenance": "dbt"})
def update_dbt_job() -> None:
    _update_dbt()


@dg.job(tags={"maintenance": "dbt"})
def update_dbt_changed_job() -> None:
    _update_dbt_changed()


@dg.job(tags={"ingestion": "scraping"})
def parsing_job() -> None:
    _run_parsing()


@dg.job(tags={"orchestration": "prefect"})
def prefect_trigger_job() -> None:
    _trigger_prefect()


@dg.job(tags={"ingestion": "cdc"})
def cdc_job() -> None:
    _run_cdc()


@dg.job(tags={"maintenance": "dbt", "package": "dbt_project_evaluator"})
def dbt_project_evaluator_job() -> None:
    _dbt_evaluate()


# --------------------------------------------------------------------------- schedules
schedules = [
    dg.ScheduleDefinition(
        name="daily_dwh_full_refresh",
        job=dwh_full_refresh_job,
        cron_schedule="0 3 * * *",  # nightly rebuild
    ),
    dg.ScheduleDefinition(
        name="hourly_dwh_incremental",
        job=dwh_incremental_job,
        cron_schedule="0 * * * *",
    ),
    dg.ScheduleDefinition(
        name="quarter_hourly_cdc",
        job=cdc_job,
        cron_schedule="*/15 * * * *",  # frequent CDC catch-up
    ),
    dg.ScheduleDefinition(
        name="daily_dbt_subproject_update",
        job=update_dbt_job,
        cron_schedule="0 2 * * *",
    ),
    dg.ScheduleDefinition(
        name="daily_raw_ingest",
        job=raw_ingest_job,
        cron_schedule="30 1 * * *",
    ),
    dg.ScheduleDefinition(
        name="weekly_dbt_project_evaluator",
        job=dbt_project_evaluator_job,
        cron_schedule="0 4 * * 1",  # Monday 04:00 — audit the dbt project
    ),
]


# --------------------------------------------------------------------------- sensors
@dg.asset_sensor(
    asset_key=RAW,
    job=dwh_assets_job,
    name="raw_landed_runs_dwh",
    description="When new raw data materializes, refresh the whole DWH (raw → stg → core → fs).",
)
def raw_landed_sensor(
    context: SensorEvaluationContext, asset_event: EventLogEntry
) -> dg.RunRequest:
    return dg.RunRequest(run_key=str(asset_event.timestamp))


@dg.sensor(
    job=dwh_incremental_job,
    minimum_interval_seconds=60,
    name="new_postgres_raw_data",
    description="Trigger the incremental DWH when the Postgres landing zone has new rows.",
)
def new_postgres_raw_sensor(context: SensorEvaluationContext) -> dg.SensorResult | dg.SkipReason:
    """Poll `landing.*` row count; run when it grows. Skips cleanly when Postgres is absent."""
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
    except Exception as exc:
        return dg.SkipReason(f"landing DB unavailable ({type(exc).__name__})")
    if context.cursor == count:
        return dg.SkipReason(f"no new landing rows (count={count})")
    return dg.SensorResult(run_requests=[dg.RunRequest(run_key=count)], cursor=count)


@dg.sensor(
    job=update_dbt_changed_job,
    minimum_interval_seconds=30,
    name="spec_change_updates_dbt",
    description="On a spec/sql change, regenerate the dbt subproject and run only changed models.",
)
def spec_change_sensor(context: SensorEvaluationContext) -> dg.SensorResult | dg.SkipReason:
    """Watch spec/sql mtimes; when they move, rebuild the changed dbt models (and code location)."""
    latest = max((p.stat().st_mtime for p in SPEC_SQL.rglob("*.sql")), default=0.0)
    token = f"{latest:.0f}"
    if context.cursor == token:
        return dg.SkipReason("spec/sql unchanged")
    return dg.SensorResult(run_requests=[dg.RunRequest(run_key=token)], cursor=token)


@dg.run_failure_sensor(
    name="dwh_run_failure_alert",
    description="Surface any failed run (hook point for the Notifier / alerting lane).",
)
def dwh_failure_sensor(context: RunFailureSensorContext) -> None:
    context.log.error(
        "run %s failed: %s", context.dagster_run.run_id, context.failure_event.message
    )


# --------------------------------------------------------------------------- asset checks
@dg.asset_check(
    asset=dg.AssetKey(["fs", "market_features"]),
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


# ------------------------------------------------------------------- partitions + backfills
# A daily-partitioned snapshot fact (the platform's `game_snapshot_fact` idea): one materialization
# per day, so history can be **backfilled** (`dg` UI backfill, or `jobs/dg-tasks.sh backfill`).
snapshot_partitions = dg.DailyPartitionsDefinition(start_date="2026-07-01")
SNAPSHOTS_DIR = REPO / ".run" / "data" / "snapshots"


@dg.asset(
    partitions_def=snapshot_partitions,
    group_name="marts",
    kinds={"duckdb", "parquet"},
    description="Daily market snapshot from fs.market_features — partitioned, backfillable.",
)
def market_snapshot(context: AssetExecutionContext) -> dg.MaterializeResult:
    date = context.partition_key
    out = SNAPSHOTS_DIR / f"date={date}"
    out.mkdir(parents=True, exist_ok=True)
    rows = 0
    if WAREHOUSE.exists():
        import duckdb

        con = duckdb.connect(str(WAREHOUSE), read_only=True)
        try:
            con.execute(
                f"copy (select date '{date}' as snapshot_date, game_sk, title, "
                f"popularity_score, critic_score from fs.market_features) "
                f"to '{out / 'snapshot.parquet'}' (format parquet)"
            )
            result = con.execute("select count(*) from fs.market_features").fetchone()
            rows = int(result[0]) if result else 0
        finally:
            con.close()
    return dg.MaterializeResult(metadata={"partition": date, "rows": rows})


market_snapshot_job = dg.define_asset_job(
    "market_snapshot_job",
    selection=dg.AssetSelection.assets(market_snapshot),
    partitions_def=snapshot_partitions,
)
# Partitioned schedule — materializes each day's partition on a daily cron (backfill-aware).
daily_snapshot_schedule = dg.build_schedule_from_partitioned_job(
    market_snapshot_job, name="daily_market_snapshot"
)


# --------------------------------------------------------------------------- definitions
defs = dg.Definitions(
    assets=[market_snapshot],
    jobs=[
        raw_ingest_job,
        staging_job,
        core_job,
        fs_job,
        dwh_assets_job,
        dlt_ingest_job,
        cdc_asset_job,
        dwh_incremental_job,
        dwh_full_refresh_job,
        update_dbt_job,
        update_dbt_changed_job,
        parsing_job,
        prefect_trigger_job,
        cdc_job,
        dbt_project_evaluator_job,
        market_snapshot_job,
    ],
    schedules=[*schedules, daily_snapshot_schedule],
    sensors=[
        raw_landed_sensor,
        new_postgres_raw_sensor,
        spec_change_sensor,
        dwh_failure_sensor,
    ],
    asset_checks=[market_features_check],
)
