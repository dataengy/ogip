"""Snapshot task — the daily market snapshot fact, one Parquet per partition date."""

from __future__ import annotations

import datetime

from ogip.config import get_settings
from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["snapshot_write"]


@odos_task("snapshot.write")
def snapshot_write(*, partition: str) -> int:
    """Write one daily partition of the market snapshot; return the row count.

    Precondition: the DuckDB warehouse must already exist (built by `dbt.build`); a
    missing warehouse raises `FileNotFoundError` rather than writing an empty partition.
    """
    try:
        datetime.date.fromisoformat(partition)
    except ValueError as exc:
        raise ValueError(f"partition must be an ISO date (YYYY-MM-DD), got {partition!r}") from exc

    import duckdb

    settings = get_settings()
    warehouse = settings.platform.warehouse_path
    if not warehouse.exists():
        raise FileNotFoundError(f"warehouse not found at {warehouse}")

    out = settings.platform.data_dir / "snapshots" / f"date={partition}"
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        # `partition` is bound as a query parameter, not interpolated — it is validated
        # above as a real ISO date, so `cast(? as date)` cannot smuggle SQL. The output
        # path still has to be interpolated: DuckDB requires the COPY ... TO target as a
        # literal, not a bindable parameter. That is safe here because `out` is built from
        # `partition`, and `partition` is already constrained to `YYYY-MM-DD` above.
        con.execute(
            "copy (select cast(? as date) as snapshot_date, game_sk, title, "
            "popularity_score, critic_score from fs.market_features) "
            f"to '{out / 'snapshot.parquet'}' (format parquet)",
            [partition],
        )
        result = con.execute("select count(*) from fs.market_features").fetchone()
    finally:
        con.close()
    rows = int(result[0]) if result else 0
    log.info("snapshot {d}: {n} rows", d=partition, n=rows)
    return rows
