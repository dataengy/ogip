"""OGIP production flow entry point (Prefect) — the M0 walking skeleton, now the SQLMesh setup.

Each SQL engine has its OWN separated Prefect setup under `pipelines/flows/engines/` (A12
run-profile matrix). This module keeps the canonical name `ingest_transform_publish` pointing at
the **production** setup (SQLMesh), so `just run-profile prefect-sqlmesh`, the e2e test, and any
deployment that imports the default flow keep working unchanged.

`ingest → transform → ml_features → publish`: RAWG → raw Parquet (dlt) → SQLMesh (staging→core→fs)
→ ML feature matrix (`experimental/python_tasks`) → ML-ready Parquet. Steps are Prefect Assets
(`@materialize`), so the datasets carry lineage in the Prefect UI. Runs ephemerally (no server).
"""

from __future__ import annotations

from pipelines.flows.engines.prefect_sqlmesh import flow as ingest_transform_publish

__all__ = ["ingest_transform_publish"]


if __name__ == "__main__":
    from ogip.logger import log

    result = ingest_transform_publish()
    log.info("M0 pipeline complete: {r}", r=result)
