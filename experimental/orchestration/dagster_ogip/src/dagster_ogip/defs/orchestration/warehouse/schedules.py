"""Warehouse schedules — the cron cadence for the DWH jobs defined in `jobs.py`."""

import dagster as dg
from dagster_ogip.defs.orchestration.warehouse.jobs import (
    dwh_full_refresh_job,
    dwh_incremental_job,
    raw_ingest_job,
)

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


defs = dg.Definitions(schedules=schedules)
