"""Prefect setup for the **plain-SQL runner** — the `prefect-sql` comparison profile.

Separated setup (A12): ingest (dlt) → framework-free SQL runner (topo-sort `depends`,
`create or replace` on DuckDB) → ML feature matrix → ML-ready Parquet. Shares step logic with
every other engine via `pipelines.flows._common`.
"""

from __future__ import annotations

from pipelines.flows._common import make_engine_flow

flow = make_engine_flow("plain_sql")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("plain_sql pipeline complete: {r}", r=flow())
