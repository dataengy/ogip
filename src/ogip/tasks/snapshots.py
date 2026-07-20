"""Snapshot task — the daily market snapshot fact, one Parquet per partition date."""

from __future__ import annotations

from ogip.config import get_settings
from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["snapshot_write"]


@odos_task("snapshot.write")
def snapshot_write(*, partition: str) -> int:
    """Write one daily partition of the market snapshot; return the row count."""
    import duckdb

    settings = get_settings()
    warehouse = settings.platform.warehouse_path
    out = settings.platform.data_dir / "snapshots" / f"date={partition}"
    out.mkdir(parents=True, exist_ok=True)
    if not warehouse.exists():
        log.warning("warehouse absent at {p} — snapshot skipped", p=warehouse)
        return 0
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        con.execute(
            f"copy (select date '{partition}' as snapshot_date, game_sk, title, "
            f"popularity_score, critic_score from fs.market_features) "
            f"to '{out / 'snapshot.parquet'}' (format parquet)"
        )
        result = con.execute("select count(*) from fs.market_features").fetchone()
    finally:
        con.close()
    rows = int(result[0]) if result else 0
    log.info("snapshot {d}: {n} rows", d=partition, n=rows)
    return rows
