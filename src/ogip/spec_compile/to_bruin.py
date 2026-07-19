"""Render `spec/sql` into a runnable Bruin pipeline — a pass-through, since spec *is* Bruin.

Assets are copied verbatim (the ``@bruin`` header already carries name/type/materialization/
depends/checks); this generator only adds the shell the Bruin CLI needs: ``pipeline.yml``,
``.bruin.yml`` (the DuckDB connection → the warehouse), and the ``assets/`` tree. Paths stay
repo-relative, so ``bruin validate``/``run`` must execute from the repo root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .bruin import asset_paths, parse_asset

_CONNECTION = "ogip-duckdb"

_README = """# `transform/bruin/` — GENERATED from `spec/` (do not hand-edit)

Bruin pipeline for the `prefect-bruin` profile — a pass-through: `spec/sql` is authored in
Bruin asset format, so assets are copied verbatim and only the project shell is added.
Regenerate: `just spec-compile bruin`. Run from the repo root: `bruin run transform/bruin`.
"""


def compile_to_bruin(spec_sql_dir: Path, project_dir: Path, *, warehouse: Path) -> list[str]:
    """Generate a Bruin pipeline under ``project_dir`` from ``spec/sql``; return asset names."""
    assets_dir = project_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for stale in assets_dir.rglob("*.sql"):  # regenerate cleanly
        stale.unlink()

    names: list[str] = []
    for path in asset_paths(spec_sql_dir):
        asset = parse_asset(path)  # parse to validate + derive the layout; copy stays verbatim
        target = assets_dir / asset.schema / f"{asset.model}.sql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        names.append(asset.name)

    pipeline: dict[str, Any] = {
        "name": "ogip",
        "default_connections": {"duckdb": _CONNECTION},
    }
    (project_dir / "pipeline.yml").write_text(
        yaml.safe_dump(pipeline, sort_keys=False), encoding="utf-8"
    )
    environments: dict[str, Any] = {
        "default_environment": "default",
        "environments": {
            "default": {"connections": {"duckdb": [{"name": _CONNECTION, "path": str(warehouse)}]}}
        },
    }
    (project_dir / ".bruin.yml").write_text(
        yaml.safe_dump(environments, sort_keys=False), encoding="utf-8"
    )
    (project_dir / ".gitignore").write_text("logs/\n", encoding="utf-8")
    (project_dir / "README.md").write_text(_README, encoding="utf-8")
    return names
