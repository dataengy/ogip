"""Warehouse sensors — event/poll triggers that drive the DWH jobs in `jobs.py`."""

import dagster as dg
from dagster import SensorEvaluationContext
from dagster_ogip._lib.orchestration import K_RAW_DLT
from dagster_ogip.defs.orchestration.warehouse.jobs import dwh_assets_job, dwh_incremental_job


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
    import os

    # A missing driver is a DEPLOYMENT fault, not "the DB is down" — keep it distinguishable.
    # Folding ImportError into the generic handler below made this sensor skip forever with a
    # plausible "landing DB unavailable" message even when the DB was healthy.
    try:
        import psycopg
    except ImportError:
        return dg.SkipReason(
            "psycopg is not installed — the landing-DB driver is missing from this deployment, "
            "so this sensor cannot poll (this is a packaging fault, NOT an unreachable DB)"
        )

    dsn = os.environ.get("OGIP_PG_DSN")
    if not dsn:
        return dg.SkipReason("OGIP_PG_DSN not set — no landing DB to watch")
    try:
        with psycopg.connect(dsn) as conn:
            total = conn.execute(
                "select coalesce(sum(n_live_tup), 0) from pg_stat_user_tables "
                "where schemaname = 'landing'"
            ).fetchone()
        count = str(total[0] if total else 0)
    except Exception as exc:  # sensor must never crash the daemon
        return dg.SkipReason(f"landing DB unavailable ({type(exc).__name__}: {exc})"[:250])
    if context.cursor == count:
        return dg.SkipReason(f"no new landing rows (count={count})")
    return dg.SensorResult(run_requests=[dg.RunRequest(run_key=count)], cursor=count)


defs = dg.Definitions(sensors=[raw_landed_sensor, new_postgres_raw_sensor])
