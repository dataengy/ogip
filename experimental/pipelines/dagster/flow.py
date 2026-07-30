"""Prefect setup that calls **Dagster for dlt+dbt only**, wrapping everything else in Prefect.

The division of labour the platform wants: Dagster owns the narrow, asset-graph-shaped part it is
best at — the **dlt ingestion + dbt transform** combo (`experimental/orchestration/dagster_ogip`,
run via `dg launch`) — while **Prefect** owns the rest of the platform (scraping, infra,
observability, alerting, and the **ML** feature step). This flow is the seam: one Prefect asset
triggers the Dagster dlt+dbt materialization, then Prefect runs the ML feature matrix and publish.

Prerequisite: the Dagster project has its own uv env (`cd experimental/orchestration/dagster_ogip
&& uv sync`) and the `dg` CLI. Without them the Dagster step raises a clear, actionable error.

Separately deployable (prefect.yaml) — moved here from `pipelines/flows/engines/prefect_dagster.py`
in Part 3.2; that module (and the rest of `pipelines/flows/engines/`) was deleted in Part 3.3 once
every consumer resolved through `pipelines._shared.engines.ENGINE_FLOWS` instead.
"""

from __future__ import annotations

import shutil
import subprocess

from pipelines._shared.alerting import notify_flow_failure
from pipelines._shared.paths import REPO
from pipelines._shared.steps import build_ml_outputs, publish_outputs
from prefect import flow
from prefect.assets import materialize

from ogip.config import get_settings
from ogip.logger import log, setup_logging
from ogip.spec_compile.to_dbt import compile_to_dbt
from ogip.tasks.ingest import ingest_scraped

DAGSTER_PROJECT = REPO / "experimental" / "orchestration" / "dagster_ogip"
# The two Dagster asset selections making up the dlt→dbt combo (see dagster_ogip/e2e/run_combo.sh):
# the dlt source asset, then EVERY dbt model. `kind:"dbt"` (not `key:"rawg__games"+`): the
# cross-source core models read scraped-source staging that is NOT downstream of the rawg
# key, so the `+`-selection built core without its scraped parents — green only on a warehouse
# that already carried them, "Catalog Error: table does not exist" on a clean slate (the
# standing combo-e2e failure on dev).
_DLT_ASSET = 'key:"raw/rawg__games"'
_DBT_SUBGRAPH = 'kind:"dbt"'

SCRAPED_RAW_KEY = "file://ogip/dagster/raw/scraped"
RAW_KEY = "file://ogip/dagster/raw/rawg__games"
WAREHOUSE_KEY = "duckdb://ogip/dagster/warehouse"
ML_KEY = "file://ogip/dagster/outputs/ml_features.parquet"
OUT_KEY = "file://ogip/dagster/outputs/games.parquet"


def run_dagster_dlt_dbt() -> list[str]:
    """Materialize the dlt ingestion + dbt transform through Dagster; return the asset selections.

    Shells `dg launch` inside the Dagster project's own env — Dagster (1.13.x) pins deps the main
    OGIP env does not carry, so it stays isolated under `experimental/`.
    """
    if shutil.which("uv") is None:  # dg is invoked via `uv run` in the project env
        raise RuntimeError("uv not on PATH — needed to run the Dagster project's `dg` CLI")
    if not (DAGSTER_PROJECT / "pyproject.toml").is_file():
        raise RuntimeError(f"Dagster project not found at {DAGSTER_PROJECT}")
    # Regenerate the project's dbt render from spec/ (mirrors e2e/run_combo.sh step 1). This
    # project is UNTRACKED runtime output, and Dagster's DbtProjectComponent stages a copy
    # under .local_defs_state/ — so paths must be ABSOLUTE here (a relative warehouse path
    # resolves inside the staged copy and the build dies on "cannot open database"). The
    # tracked transform/dbt render is the opposite case: portable paths, cwd=repo.
    models = compile_to_dbt(
        REPO / "spec" / "sql",
        DAGSTER_PROJECT / "dbt",
        warehouse=get_settings().platform.warehouse_path.resolve(),
        repo_root=REPO,
    )
    log.bind(orchestrator="dagster").info("regenerated dagster dbt render: {n} models", n=len(models))
    for selection in (_DLT_ASSET, _DBT_SUBGRAPH):
        log.bind(orchestrator="dagster").info("dg launch --assets {s}", s=selection)
        subprocess.run(
            ["uv", "run", "dg", "launch", "--assets", selection],
            check=True,
            cwd=DAGSTER_PROJECT,
        )
    return [_DLT_ASSET, _DBT_SUBGRAPH]


@materialize(SCRAPED_RAW_KEY)
def _ingest_scraped() -> str:
    """Prefect owns scraping: land the enabled scraped sources' raw Parquet OUTSIDE dlt.

    Runs BEFORE the Dagster dbt build so the cross-source dbt models (critic_reception,
    console_pricing, traction) have their scraped-source staging to read. Scrapers are not dlt
    sources, so Dagster's dlt asset only covers RAWG — this is the missing half of ingestion.
    """
    ingest_scraped()
    return SCRAPED_RAW_KEY


@materialize(RAW_KEY, WAREHOUSE_KEY)
def _dagster_dlt_dbt(_scraped: str) -> list[str]:
    """Dagster owns dlt+dbt: source → raw Parquet → dbt build → core/fs in the shared warehouse."""
    return run_dagster_dlt_dbt()


@materialize(ML_KEY)
def _ml_features(_dagster: list[str]) -> dict[str, int]:
    """Prefect owns ML: feature tasks over the warehouse Dagster just built."""
    return build_ml_outputs()


@materialize(OUT_KEY)
def _publish(_ml: dict[str, int]) -> dict[str, int]:
    """Prefect owns publish: export core/fs to ML-ready Parquet."""
    return publish_outputs()


@flow(name="dagster_dlt_dbt_wrapped_in_prefect", on_failure=[notify_flow_failure])
def flow_dagster() -> dict[str, int]:
    """Dagster (dlt+dbt) wrapped in Prefect (ML + publish + alerting)."""
    setup_logging()
    scraped = _ingest_scraped()
    dagster_assets = _dagster_dlt_dbt(scraped)
    ml = _ml_features(dagster_assets)
    outputs = _publish(ml)
    return {**outputs, **{f"ml::{k}": v for k, v in ml.items()}}


flow = flow_dagster

if __name__ == "__main__":
    log.info("dagster-in-prefect pipeline complete: {r}", r=flow())
