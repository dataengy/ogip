"""Ingestion jobs — getting source data into the platform.

dlt is the default ingester (batch API sources); ingestr does CDC from the Postgres landing
zone; parsing is the scraper→landing step (placeholder until the ingestion lane picks a tool).
"""

import dagster as dg
from dagster import OpExecutionContext
from dagster_ogip._lib.orchestration import K_CDC, K_RAW_DLT, run_task

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


class CdcConfig(dg.Config):
    """`dry_run` prints the ingestr command and touches nothing — for demos off a live DB.

    Defaults to FALSE so the job actually performs CDC. It was previously hardcoded to
    `--dry-run`, which made every run a silent no-op that still reported success — the job
    could not do real CDC even when triggered by hand, and a green run meant nothing.
    """

    dry_run: bool = False


@dg.op
def _run_cdc(context: OpExecutionContext, config: CdcConfig) -> None:
    if config.dry_run:
        run_task(context, "cdc", "--dry-run")
    else:
        run_task(context, "cdc")


@dg.op
def _run_parsing(context: OpExecutionContext) -> None:
    run_task(context, "parsing")


@dg.job(
    tags={"ingestion": "cdc"},
    description="ingestr CDC catch-up — capture INSERT/UPDATE/DELETE on the Postgres `landing` "
    "schema via logical replication and merge into the lake. Performs REAL CDC by default; pass "
    "op config `_run_cdc: {dry_run: true}` to only print the command. Fails loudly when CDC is "
    "unconfigured (blank OGIP_PG_PASSWORD), same as cdc_asset_job.",
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
        description="Frequent (every 15 min) CDC catch-up from the landing zone. STOPPED by "
        "default (Dagster's default status) and must stay so until the CDC prerequisites exist: "
        "a reachable landing DB with `wal_level=logical` and "
        "`CREATE PUBLICATION ogip_landing_pub FOR TABLES IN SCHEMA landing` (a DBA/VPS step, see "
        "docs/runbooks/run-dagster.md). Enabled before that, every tick fails on purpose.",
    ),
]


defs = dg.Definitions(
    jobs=[dlt_ingest_job, cdc_asset_job, cdc_job, parsing_job], schedules=schedules
)
