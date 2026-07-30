"""Transform engine -> its separated Prefect sub-project module (one flow each).

The two PRIMARY comparison candidates (dbt, bruin) live on the default path under
``pipelines/``; the five demoted engines are comparison/experimental setups under
``experimental/pipelines/`` (re-root #40). Only the module path differs.
"""

from __future__ import annotations

ENGINE_FLOWS: dict[str, str] = {
    # primary candidates — on the default path
    "dbt": "pipelines.dbt.flow",
    "bruin": "pipelines.bruin.flow",
    # experimental / comparison setups — off the default path
    "sqlmesh": "experimental.pipelines.sqlmesh.flow",
    "plain_sql": "experimental.pipelines.plain_sql.flow",
    "opendbt": "experimental.pipelines.opendbt.flow",
    "sqlmesh_dbt": "experimental.pipelines.sqlmesh_dbt.flow",
    "dagster": "experimental.pipelines.dagster.flow",
}
