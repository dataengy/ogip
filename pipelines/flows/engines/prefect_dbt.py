"""Prefect setup for the **dbt** transform — the `prefect-dbt` comparison profile.

Separated setup (A12): ingest (dlt) → generated dbt project (`dbt deps` + `dbt build`) → ML
feature matrix → ML-ready Parquet. Shares step logic via `pipelines.flows._common`.
"""

from __future__ import annotations

from pipelines.flows._common import make_engine_flow

flow = make_engine_flow("dbt")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("dbt pipeline complete: {r}", r=flow())
