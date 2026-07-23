"""Prefect sub-project for the dbt transform setup — separately deployable (prefect.yaml)."""

from __future__ import annotations

from pipelines._shared.steps import make_engine_flow

flow = make_engine_flow("dbt")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("dbt pipeline complete: {r}", r=flow())
