"""Separated per-engine Prefect setups — one flow module per SQL-tool (A12 run-profile matrix).

Each ``prefect_<engine>.py`` exposes exactly one flow object (``flow``). ``ENGINE_FLOWS`` maps a
transform-engine name to its module path so ``src/scripts/run-profile.py`` and the e2e tests can
launch any setup without importing all of them eagerly (Dagster deps stay optional).
"""

from __future__ import annotations

# transform engine (config → run_profiles[].transform) → its "pipelines.flows.engines.*" module
ENGINE_FLOWS: dict[str, str] = {
    "sqlmesh": "pipelines.flows.engines.prefect_sqlmesh",
    "plain_sql": "pipelines.flows.engines.prefect_sql",
    "dbt": "pipelines.flows.engines.prefect_dbt",
    "opendbt": "pipelines.flows.engines.prefect_opendbt",
    "sqlmesh_dbt": "pipelines.flows.engines.prefect_sqlmesh_dbt",
    "bruin": "pipelines.flows.engines.prefect_bruin",
    "dagster": "pipelines.flows.engines.prefect_dagster",
}
