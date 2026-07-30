"""Prefect sub-project for the plain-SQL runner — separately deployable (prefect.yaml).

The `prefect-sql` comparison profile: ingest (dlt) → framework-free SQL runner (topo-sort
`depends`, `create or replace` on DuckDB) → ML feature matrix → ML-ready Parquet. Shares step
logic with every other engine via `pipelines._shared.steps`.
"""

from __future__ import annotations

from pipelines._shared.steps import make_engine_flow

flow = make_engine_flow("plain_sql")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("plain_sql pipeline complete: {r}", r=flow())
