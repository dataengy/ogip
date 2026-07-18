"""OGIP production flow (Prefect) — the M0 walking skeleton.

`ingest_transform_publish`: RAWG → raw Parquet (dlt) → SQLMesh (staging→core→fs) → ML-ready
Parquet outputs. Runs ephemerally (no server needed); `integrations/prefect/` deploys it.

Steps are declared with Prefect **Assets** (`@materialize`), so the platform's datasets — raw
Parquet, warehouse relations, ML outputs — carry lineage in the Prefect UI instead of being
opaque tasks. Keys are logical (stable across machines), not absolute paths.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ingestion.sources.rawg import RawgGames
from pipelines.alerting_hooks import notify_flow_failure
from prefect import flow
from prefect.assets import materialize

from ogip.config import get_settings
from ogip.logger import logger, setup_logging
from ogip.spec_compile import compile_to_sqlmesh
from ogip.warehouse import export_table

REPO = Path(__file__).resolve().parents[2]
SPEC_SQL = REPO / "spec" / "sql"
SQLMESH_DIR = REPO / "transform" / "sqlmesh"

# --- Assets (logical keys; lineage: raw → core/fs → ML outputs) ---
RAW_GAMES = "file://ogip/raw/rawg__games"
CORE_GAME = "duckdb://ogip/core.game"
FS_MARKET_FEATURES = "duckdb://ogip/fs.market_features"
OUT_GAMES = "file://ogip/outputs/games.parquet"
OUT_MARKET_FEATURES = "file://ogip/outputs/market_features.parquet"


@materialize(RAW_GAMES)
def ingest() -> str:
    """Extract RAWG games via dlt → raw Parquet (Layer 0)."""
    settings = get_settings()
    out = RawgGames(settings).run(settings.platform.data_dir)
    logger.bind(source="rawg").info("raw landed at {p}", p=out)
    return str(out)


@materialize(CORE_GAME, FS_MARKET_FEATURES)
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


@materialize(OUT_GAMES, OUT_MARKET_FEATURES)
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


@flow(name="ingest_transform_publish", on_failure=[notify_flow_failure])
def ingest_transform_publish() -> dict[str, int]:
    """The daily driver — ingest → transform → publish (asset lineage via @materialize)."""
    settings = get_settings()
    # Write a structured log file so the obs stack (Alloy → Loki) has something to tail, and
    # honor the SSoT json/level knobs instead of a bare default.
    setup_logging(json_logs=settings.platform.log_json, log_file=settings.platform.log_file)
    raw = ingest()
    models = transform(raw)
    return publish(models)


if __name__ == "__main__":
    result = ingest_transform_publish()
    logger.info("M0 pipeline complete: {r}", r=result)
