"""Prefect setup for **SQLMesh-over-dbt** — the `prefect-sqlmesh-over-dbt` comparison profile.

Separated setup (A12): ingest (dlt) → SQLMesh plans/applies the generated dbt project natively
→ ML feature matrix → ML-ready Parquet. Shares step logic via `pipelines.flows._common`.
"""

from __future__ import annotations

from pipelines.flows._common import make_engine_flow

flow = make_engine_flow("sqlmesh_dbt")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("sqlmesh_dbt pipeline complete: {r}", r=flow())
