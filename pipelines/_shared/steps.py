"""Shared building blocks for the separated per-engine Prefect setups.

Each SQL engine gets its OWN Prefect flow module under ``engines/`` (one separated setup per
the run-profile matrix, ADR-0007 / A12). They all reuse the plain step functions here, so the
only thing that differs between setups is the transform engine and its asset namespace. The
steps are decorator-free (unit-testable, importable without a Prefect runtime); ``make_engine_flow``
wraps them into a flow whose assets carry per-engine lineage in the Prefect UI:

    raw Parquet → warehouse (core/fs) → ML feature matrix → published ML-ready Parquet

The ML step crosses into ``experimental/python_tasks`` behind a typed ``dict[str, int]`` boundary
(``build_ml_features``) — pandas never enters this pyright-strict module.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from pipelines._shared.alerting import notify_flow_failure
from pipelines._shared.paths import REPO, SPEC_SQL, SQLMESH_DIR
from prefect import flow
from prefect.assets import materialize

from ogip.config import get_settings
from ogip.logger import log, setup_logging
from ogip.spec_compile import compile_to_sqlmesh, load_assets
from ogip.tasks.dbt import dbt_build
from ogip.tasks.ingest import ingest_all
from ogip.warehouse import export_table

if TYPE_CHECKING:
    from prefect import Flow


# --- Plain step functions (engine-agnostic; no Prefect decoration) ---


# Layer 0 ingestion is a registry task — the SAME callable the Dagster lane runs, not a
# parallel implementation of it. Re-exported under the historical name so `make_engine_flow`
# and every `engines/prefect_*.py` module stay untouched. Enablement still comes from config
# SSoT (`sources.<name>.enabled`); it moved into `ingest.all`, it did not disappear.
ingest_raw = ingest_all


def build_warehouse(engine: str) -> list[str]:
    """Build ``staging → core → fs`` with ``engine``; return the model names.

    ``sqlmesh`` is the production path (compile spec → SQLMesh → plan). Every other engine is a
    comparison setup delegated to ``transform.engines`` (regenerate-from-spec then run).
    """
    get_settings().platform.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    if engine == "sqlmesh":
        models = compile_to_sqlmesh(SPEC_SQL, SQLMESH_DIR / "models")
        log.info("compiled {n} SQLMesh models: {m}", n=len(models), m=models)
        subprocess.run(
            ["sqlmesh", "-p", str(SQLMESH_DIR), "plan", "--auto-apply", "--no-prompts"],
            check=True,
            cwd=REPO,
        )
        return models
    if engine == "dbt":
        # The registry task — the same code path and flags the Dagster lane runs.
        dbt_build(project_dir=REPO / "transform" / "dbt")
        return [asset.name for asset in load_assets(SPEC_SQL)]
    from transform.engines import run_transform_engine

    return run_transform_engine(engine)


def build_ml_outputs() -> dict[str, int]:
    """Run the pandas/Polars ML feature tasks over the warehouse; return per-file row counts.

    Typed boundary: ``build_ml_features`` returns ``dict[str, int]`` and keeps every dataframe
    inside ``experimental/python_tasks`` (off the pyright-strict path).
    """
    from experimental.python_tasks.pipeline import build_ml_features

    settings = get_settings()
    counts = build_ml_features(settings.platform.warehouse_path, settings.platform.outputs_dir)
    log.info("ML feature outputs {c}", c=counts)
    return counts


def publish_outputs() -> dict[str, int]:
    """Export core/FS relations to ML-ready Parquet outputs; return row counts."""
    settings = get_settings()
    wh, outdir = settings.platform.warehouse_path, settings.platform.outputs_dir
    counts = {
        "games.parquet": export_table(wh, "core.game", outdir / "games.parquet"),
        "market_features.parquet": export_table(
            wh, "fs.market_features", outdir / "market_features.parquet"
        ),
    }
    log.info("published outputs {c}", c=counts)
    return counts


def make_engine_flow(engine: str, *, flow_name: str | None = None) -> Flow[[], dict[str, int]]:
    """Build a separated Prefect flow for one SQL engine.

    Asset keys are namespaced by engine (``…/<engine>/…``) so each setup shows its own lineage
    in the Prefect UI even when several run against the same warehouse. Returns the flow object;
    each ``engines/prefect_<engine>.py`` module exposes exactly one.
    """
    name = flow_name or f"ingest_transform_publish_{engine}"
    raw_key = f"file://ogip/{engine}/raw/rawg__games"
    core_key = f"duckdb://ogip/{engine}/core.game"
    fs_key = f"duckdb://ogip/{engine}/fs.market_features"
    ml_key = f"file://ogip/{engine}/outputs/ml_features.parquet"
    out_key = f"file://ogip/{engine}/outputs/games.parquet"

    @materialize(raw_key)
    def _ingest() -> str:
        return ingest_raw()

    @materialize(core_key, fs_key)
    def _transform(_raw: str) -> list[str]:
        return build_warehouse(engine)

    @materialize(ml_key)
    def _ml_features(_models: list[str]) -> dict[str, int]:
        return build_ml_outputs()

    @materialize(out_key)
    def _publish(_ml: dict[str, int]) -> dict[str, int]:
        return publish_outputs()

    @flow(name=name, on_failure=[notify_flow_failure])
    def _engine_flow() -> dict[str, int]:
        # Structured log file so the obs stack (Alloy → Loki) has something to tail; honor the
        # SSoT json/level knobs instead of a bare default (obs handoff — core-pipeline lane, #29).
        _platform = get_settings().platform
        setup_logging(json_logs=_platform.log_json, log_file=_platform.log_file)
        raw = _ingest()
        models = _transform(raw)
        ml = _ml_features(models)
        outputs = _publish(ml)
        return {**outputs, **{f"ml::{k}": v for k, v in ml.items()}}

    return _engine_flow
