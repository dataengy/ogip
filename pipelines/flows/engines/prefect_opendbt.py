"""Prefect setup for **OpenDBT** — the `prefect-opendbt` comparison profile.

Separated setup (A12): ingest (dlt) → OpenDBT (dbt-core extended) over the generated project,
run through its own dep group → ML feature matrix → ML-ready Parquet. Shares step logic via
`pipelines.flows._common`.
"""

from __future__ import annotations

from pipelines.flows._common import make_engine_flow

flow = make_engine_flow("opendbt")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("opendbt pipeline complete: {r}", r=flow())
