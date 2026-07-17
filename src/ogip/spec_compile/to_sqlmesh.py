"""Render parsed Bruin assets into SQLMesh model files.

SQLMesh infers dependencies from the SQL (`FROM schema.model`), so the Bruin `depends` stays
documentation; we only translate `name` + materialization into a `MODEL(...)` block.
"""

from __future__ import annotations

from pathlib import Path

from .bruin import Asset, load_assets

_KIND = {"table": "FULL", "view": "VIEW"}


def _model_text(asset: Asset) -> str:
    kind = _KIND.get(asset.materialization, "FULL")
    header = f"MODEL (\n  name {asset.name},\n  kind {kind}\n);\n\n"
    return header + asset.sql + "\n"


def compile_to_sqlmesh(spec_sql_dir: Path, models_dir: Path) -> list[str]:
    """Generate SQLMesh models under ``models_dir`` from ``spec/sql``; return model names."""
    assets = load_assets(spec_sql_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    for stale in models_dir.rglob("*.sql"):  # regenerate cleanly
        stale.unlink()
    for asset in assets:
        target = models_dir / asset.schema / f"{asset.model}.sql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_model_text(asset), encoding="utf-8")
    return [asset.name for asset in assets]
