"""OGIP production flow entry point (Prefect) — now the **dbt** primary candidate.

The two primary comparison candidates are **dbt** and **bruin**, each a separately-deployable
Prefect sub-project under `pipelines/<engine>/` (re-root #40); the other engines are comparison
setups under `experimental/pipelines/`. This module keeps the canonical name
`ingest_transform_publish` pointing at the default primary (dbt), so the e2e test and any
deployment that imports the default flow keep working. `src/ogip/tasks/integrations.py` shells
`python -m pipelines.flows.main` — this module MUST stay importable at this exact path.

`ingest → transform → ml_features → publish`: RAWG → raw Parquet (dlt) → dbt (staging→core→fs)
→ ML feature matrix (`experimental/python_tasks`) → ML-ready Parquet. Steps are Prefect Assets
(`@materialize`), so the datasets carry lineage in the Prefect UI. Runs ephemerally (no server).
"""

from __future__ import annotations

from pipelines.dbt.flow import flow as ingest_transform_publish

__all__ = ["ingest_transform_publish"]


if __name__ == "__main__":
    from ogip.logger import log

    result = ingest_transform_publish()
    log.info("M0 pipeline complete: {r}", r=result)
