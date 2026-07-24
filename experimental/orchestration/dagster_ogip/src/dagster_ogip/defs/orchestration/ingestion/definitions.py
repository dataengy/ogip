"""Ingestion jobs — getting source data into the platform.

dlt is the default ingester (batch API sources); ingestr does CDC from the Postgres landing
zone; parsing is the scraper→landing step (placeholder until the ingestion lane picks a tool).
"""

from dagster_ogip._lib.orchestration import K_CDC, K_RAW_DLT, run_task

import dagster as dg
from dagster import OpExecutionContext

dlt_ingest_job = dg.define_asset_job(
    "dlt_ingest_job",
    selection=dg.AssetSelection.assets(K_RAW_DLT),
    description="Run the dlt RAWG load (clean REST API → raw Parquet). The default ingestion path.",
)
cdc_asset_job = dg.define_asset_job(
    "cdc_asset_job",
    selection=dg.AssetSelection.assets(K_CDC),
    description="Materialize the ingestr CDC asset (Postgres landing → lake) as part of the graph.",
)


@dg.op
def _run_cdc(context: OpExecutionContext) -> None:
    run_task(context, "cdc", "--dry-run")


@dg.op
def _run_parsing(context: OpExecutionContext) -> None:
    run_task(context, "parsing")


@dg.job(
    tags={"ingestion": "cdc"},
    description="ingestr CDC catch-up — capture INSERT/UPDATE/DELETE on the Postgres `landing` "
    "schema via logical replication and merge into the lake. Runs `--dry-run` off a live DB.",
)
def cdc_job() -> None:
    _run_cdc()


@dg.job(
    tags={"ingestion": "scraping"},
    description="Run the scraper/parser → Postgres landing. Placeholder until the ingestion lane "
    "chooses an async ScraperSource tool (ADR-0014); wired here when it lands.",
)
def parsing_job() -> None:
    _run_parsing()


schedules = [
    dg.ScheduleDefinition(
        name="quarter_hourly_cdc",
        job=cdc_job,
        cron_schedule="*/15 * * * *",
        description="Frequent (every 15 min) CDC catch-up from the landing zone.",
    ),
]


defs = dg.Definitions(
    jobs=[dlt_ingest_job, cdc_asset_job, cdc_job, parsing_job], schedules=schedules
)
