"""Partitioned snapshots — the daily market snapshot fact, and the backfills it enables."""

import dagster as dg
from dagster import AssetExecutionContext
from dagster_ogip._lib.orchestration import SNAPSHOTS_DIR, WAREHOUSE, snapshot_partitions


@dg.asset(
    partitions_def=snapshot_partitions,
    group_name="marts",
    kinds={"duckdb", "parquet"},
    description="Daily market snapshot fact (one row per game per day) written from "
    "fs.market_features to a per-date Parquet — daily-partitioned, so history is backfillable.",
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
    description="Materialize one daily partition of market_snapshot (backfill a range from the UI "
    "or `dagster asset backfill market_snapshot --partitions ...`).",
)
daily_snapshot_schedule = dg.build_schedule_from_partitioned_job(
    market_snapshot_job, name="daily_market_snapshot"
)


defs = dg.Definitions(
    assets=[market_snapshot],
    jobs=[market_snapshot_job],
    schedules=[daily_snapshot_schedule],
)
