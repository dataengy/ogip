"""Plain-SQL runner — the `prefect-sql` comparison profile.

No transform framework at all: parse `spec/sql` (Bruin format), topo-sort on the `depends`
lineage the spec already declares, and `create or replace` each relation on the DuckDB
warehouse. This is the baseline `docs/comparisons/plain-sql-vs-frameworks.md` measures the
engines against — plans, state, and virtual environments are exactly what this file does not
have.

Run: `just run-profile prefect-sql`, or directly `uv run python transform/runner.py`.
"""

from __future__ import annotations

from graphlib import TopologicalSorter
from pathlib import Path

import duckdb

from ogip.config import get_settings
from ogip.logger import log
from ogip.spec_compile import Asset, load_assets

_REPO = Path(__file__).resolve().parents[1]


def execution_order(assets: list[Asset]) -> list[Asset]:
    """Dependency order from `depends`; references outside the spec (raw inputs) are inert."""
    by_name = {asset.name: asset for asset in assets}
    graph = {asset.name: [d for d in asset.depends if d in by_name] for asset in assets}
    return [by_name[name] for name in TopologicalSorter(graph).static_order()]


def _drop_existing(con: duckdb.DuckDBPyConnection, asset: Asset) -> None:
    """Drop any object already at ``asset.name`` — of EITHER type — before we recreate it.

    The comparison engines share one warehouse; SQLMesh leaves a virtual-layer *view* where the
    plain-SQL runner wants a *table* (and vice-versa), and ``create or replace <type>`` refuses to
    swap across object types. Look up the real type and drop it with the matching keyword +
    ``cascade`` (dependents are rebuilt in order right after).
    """
    row = con.execute(
        "select table_type from information_schema.tables "
        "where table_schema = ? and table_name = ?",
        [asset.schema, asset.model],
    ).fetchone()
    if row is not None:
        kind = "view" if row[0] == "VIEW" else "table"
        con.execute(f"drop {kind} if exists {asset.name} cascade")


def _ddl(asset: Asset) -> str:
    relation = "view" if asset.materialization == "view" else "table"
    # Spec SQL carries repo-relative runtime paths ('.run/…') — resolve them here so the
    # runner works regardless of the caller's cwd.
    sql = asset.sql.replace("'.run/", f"'{_REPO}/.run/")
    return f"create or replace {relation} {asset.name} as\n{sql}"


def run_plain_sql(spec_sql_dir: Path | None = None, warehouse: Path | None = None) -> list[str]:
    """Build every spec model on the warehouse; return the names in execution order."""
    spec_sql_dir = spec_sql_dir if spec_sql_dir is not None else _REPO / "spec" / "sql"
    warehouse = warehouse if warehouse is not None else get_settings().platform.warehouse_path
    ordered = execution_order(load_assets(spec_sql_dir))
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse))
    try:
        for asset in ordered:
            con.execute(f"create schema if not exists {asset.schema}")
            _drop_existing(con, asset)  # a prior engine may have left a view where we want a table
            con.execute(_ddl(asset))
            log.bind(engine="plain_sql").info("built {name}", name=asset.name)
    finally:
        con.close()
    return [asset.name for asset in ordered]


if __name__ == "__main__":
    built = run_plain_sql()
    log.info("plain-SQL run complete: {n} models: {names}", n=len(built), names=built)
