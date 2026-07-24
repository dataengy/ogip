"""Prefect sub-project for the sqlmesh transform setup — separately deployable (prefect.yaml)."""

from __future__ import annotations

from pipelines._shared.steps import make_engine_flow

flow = make_engine_flow("sqlmesh")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("sqlmesh pipeline complete: {r}", r=flow())
