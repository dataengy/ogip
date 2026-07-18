"""GENERATED from spec/ — SQLMesh dbt-loader entry point (do not hand-edit).

SQLMesh state lives OUTSIDE the warehouse (its own DuckDB file) so the shared warehouse
stays engine-clean — the same isolation OGAP settled on (ADR-006 there).
"""

from pathlib import Path

from sqlmesh.core.config import DuckDBConnectionConfig
from sqlmesh.dbt.loader import sqlmesh_config

_WAREHOUSE = Path(__file__).resolve().parents[2] / ".run" / "data" / "warehouse"
_WAREHOUSE.mkdir(parents=True, exist_ok=True)  # DuckDB does not create missing dirs
_STATE = _WAREHOUSE / "sqlmesh_dbt_state.duckdb"

config = sqlmesh_config(
    Path(__file__).parent,
    state_connection=DuckDBConnectionConfig(database=str(_STATE)),
)
