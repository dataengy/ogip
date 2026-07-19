"""Prefect setup for the **SQLMesh** transform — the production flow (default profile).

ingest (dlt) → SQLMesh (staging→core→fs, from spec) → ML feature matrix → ML-ready Parquet.
`pipelines/flows/main.py` re-exports this flow as the canonical `ingest_transform_publish`.
"""

from __future__ import annotations

from pipelines.flows._common import make_engine_flow

flow = make_engine_flow("sqlmesh")

if __name__ == "__main__":
    from ogip.logger import log

    log.info("sqlmesh pipeline complete: {r}", r=flow())
