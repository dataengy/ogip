"""E2E — run every separated Prefect/Dagster setup and assert it produces real results.

One test per SQL-tool setup (A12 run-profile matrix). Each cleans the warehouse, drives the same
ingest → transform → ML → publish chain the setup's Prefect flow runs (via `pipelines.flows._common`
— no ephemeral Prefect server needed; the server startup is flaky under many concurrent sessions
and is proved separately by `test_pipeline.py`), and asserts the warehouse layer + the ML feature
outputs actually materialized.

Base engines (`plain_sql`, `sqlmesh`) run in the default env and always execute. The heavy engines
(`dbt`, `opendbt`, `sqlmesh_dbt`, `bruin`) and the Dagster-wrapped setup need extra toolchains, so
they run only with `OGIP_E2E_ALL_ENGINES=1` — keeping CI fast while a full local run covers every
setup. Tests run serially (each cleans first); parallel runs need per-engine warehouses (see TODO).
"""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

import duckdb
import pytest

from ogip.config import get_settings

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.e2e

BASE_ENGINES = ["plain_sql", "sqlmesh"]
HEAVY_ENGINES = ["dbt", "opendbt", "sqlmesh_dbt", "bruin"]
_ALL_ENGINES_FLAG = "OGIP_E2E_ALL_ENGINES"


def _all_engines_enabled() -> bool:
    return os.environ.get(_ALL_ENGINES_FLAG) == "1"


def _clean_warehouse() -> None:
    """Fresh slate so each setup proves itself, not a leftover warehouse (cf. run_combo.sh)."""
    settings = get_settings()
    warehouse = settings.platform.warehouse_path
    warehouse.unlink(missing_ok=True)
    for name in ("ml_features.parquet", "ml_train.parquet", "ml_test.parquet"):
        (settings.platform.outputs_dir / name).unlink(missing_ok=True)


def _assert_warehouse_and_ml(ml_counts: dict[str, int]) -> None:
    settings = get_settings()
    warehouse = settings.platform.warehouse_path
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        core_rows = con.execute("select count(*) from core.game").fetchone()
        fs_nulls = con.execute(
            "select count(*) from fs.market_features where popularity_score is null"
        ).fetchone()
    finally:
        con.close()
    assert core_rows is not None and core_rows[0] > 0, "core.game is empty"
    assert fs_nulls is not None and fs_nulls[0] == 0, "popularity_score has nulls (contract)"

    assert ml_counts["ml_features.parquet"] > 0, "ML feature matrix is empty"
    outdir = settings.platform.outputs_dir
    for name in ("ml_features.parquet", "ml_train.parquet", "ml_test.parquet"):
        assert (outdir / name).exists(), f"missing ML output {name}"


@pytest.fixture
def _clean() -> Iterator[None]:
    _clean_warehouse()
    yield


def _run_setup_chain(engine: str) -> dict[str, int]:
    """Drive the setup exactly as its Prefect flow does — build → ML → publish."""
    from pipelines.flows import _common

    _common.build_warehouse(engine)
    ml = _common.build_ml_outputs()
    _common.publish_outputs()
    return ml


@pytest.mark.parametrize("engine", BASE_ENGINES)
def test_base_setup_builds_and_produces_ml(engine: str, _clean: None) -> None:
    _assert_warehouse_and_ml(_run_setup_chain(engine))


@pytest.mark.skipif(
    not _all_engines_enabled(), reason=f"set {_ALL_ENGINES_FLAG}=1 for heavy engines"
)
@pytest.mark.parametrize("engine", HEAVY_ENGINES)
def test_heavy_setup_builds_and_produces_ml(engine: str, _clean: None) -> None:
    if engine == "bruin" and shutil.which("bruin") is None:
        pytest.skip("bruin CLI not on PATH")
    _assert_warehouse_and_ml(_run_setup_chain(engine))


def test_default_prefect_flow_end_to_end(_clean: None) -> None:
    """The production setup through the REAL Prefect flow — proves the @materialize wiring."""
    from pipelines.flows.main import ingest_transform_publish

    counts = ingest_transform_publish()
    assert counts["games.parquet"] > 0
    assert counts["market_features.parquet"] > 0
    assert any(k.startswith("ml::") for k in counts), "ML step did not run in the flow"


@pytest.mark.skipif(
    not _all_engines_enabled(), reason=f"set {_ALL_ENGINES_FLAG}=1 for the Dagster setup"
)
def test_dagster_wrapped_in_prefect(_clean: None) -> None:
    """Dagster (dlt+dbt) wrapped in Prefect (ML+publish) — needs the Dagster project env."""
    from pipelines.flows.engines.prefect_dagster import DAGSTER_PROJECT, run_dagster_dlt_dbt

    if not (DAGSTER_PROJECT / ".venv").exists():
        pytest.skip(
            "Dagster project env not set up (cd experimental/orchestration/dagster_ogip && uv sync)"
        )
    run_dagster_dlt_dbt()
    from pipelines.flows import _common

    _assert_warehouse_and_ml(_common.build_ml_outputs())
