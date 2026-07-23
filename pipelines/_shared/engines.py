"""Transform engine -> its separated Prefect sub-project module (one flow each)."""

from __future__ import annotations

ENGINE_FLOWS: dict[str, str] = {
    "sqlmesh": "pipelines.sqlmesh.flow",
    "plain_sql": "pipelines.plain_sql.flow",
    "dbt": "pipelines.dbt.flow",
    "opendbt": "pipelines.opendbt.flow",
    "sqlmesh_dbt": "pipelines.sqlmesh_dbt.flow",
    "bruin": "pipelines.bruin.flow",
    "dagster": "pipelines.dagster.flow",
}
