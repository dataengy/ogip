"""OGIP production flow (Prefect) — the M0 walking skeleton.

`ingest_transform_publish`: RAWG → raw Parquet (dlt) → SQLMesh (staging→core→fs) → ML-ready
Parquet outputs. Runs ephemerally (no server needed); `integrations/prefect/` deploys it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ingestion.sources.rawg import RawgGames
from prefect import flow, task

from ogip.config import get_settings
from ogip.logger import logger, setup_logging
from ogip.spec_compile import compile_to_sqlmesh
from ogip.warehouse import export_table

REPO = Path(__file__).resolve().parents[2]
SPEC_SQL = REPO / "spec" / "sql"
SQLMESH_DIR = REPO / "transform" / "sqlmesh"


@task
def ingest() -> str:
    """Extract RAWG games via dlt → raw Parquet (Layer 0)."""
    settings = get_settings()
    out = RawgGames(settings).run(settings.platform.data_dir)
    logger.bind(source="rawg").info("raw landed at {p}", p=out)
    return str(out)


@task
def transform(_raw: str) -> list[str]:
    """Compile spec/ (Bruin) → SQLMesh models, then build the warehouse."""
    get_settings().platform.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    models = compile_to_sqlmesh(SPEC_SQL, SQLMESH_DIR / "models")
    logger.info("compiled {n} SQLMesh models: {m}", n=len(models), m=models)
    subprocess.run(
        ["sqlmesh", "-p", str(SQLMESH_DIR), "plan", "--auto-apply", "--no-prompts"],
        check=True,
        cwd=REPO,
    )
    return models


@task
def publish(_models: list[str]) -> dict[str, int]:
    """Export core/FS relations to ML-ready Parquet outputs."""
    settings = get_settings()
    wh, outdir = settings.platform.warehouse_path, settings.platform.outputs_dir
    counts = {
        "games.parquet": export_table(wh, "core.game", outdir / "games.parquet"),
        "market_features.parquet": export_table(
            wh, "fs.market_features", outdir / "market_features.parquet"
        ),
    }
    logger.info("published outputs {c}", c=counts)
    return counts


@flow(name="ingest_transform_publish")
def ingest_transform_publish() -> dict[str, int]:
    """The daily driver — ingest → transform → publish."""
    setup_logging()
    raw = ingest()
    models = transform(raw)
    return publish(models)


if __name__ == "__main__":
    result = ingest_transform_publish()
    logger.info("M0 pipeline complete: {r}", r=result)
