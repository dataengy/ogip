"""Prefect sub-project for the opendbt transform setup — separately deployable (prefect.yaml)."""

from __future__ import annotations

from pipelines._shared.steps import make_engine_flow

flow = make_engine_flow("opendbt")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("opendbt pipeline complete: {r}", r=flow())
