"""DuckDB warehouse helpers — export built relations to ML-ready Parquet outputs."""

from __future__ import annotations

from pathlib import Path

import duckdb


def export_table(warehouse: Path, relation: str, out_path: Path) -> int:
    """Copy ``relation`` from the DuckDB warehouse to ``out_path`` (Parquet). Return row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        con.execute(f"copy (select * from {relation}) to '{out_path}' (format parquet)")
        row = con.execute(f"select count(*) from {relation}").fetchone()
        return int(row[0]) if row is not None else 0
    finally:
        con.close()
