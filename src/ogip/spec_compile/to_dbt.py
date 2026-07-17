"""Render parsed Bruin assets into a dbt project (ADR-0005).

The `dagster_dbt.DbtProjectComponent` needs a real dbt project, but `spec/` stays the SSoT —
so we generate one. Bruin's schema-qualified deps (`from staging.stg_games`) are rewritten to
dbt `{{ ref('stg_games') }}`, and Bruin column checks become dbt tests in `schema.yml`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

import yaml

from .bruin import Asset, load_assets

_MATERIALIZATION = {"table": "table", "view": "view"}
# Bruin check name -> dbt generic test name
_TEST = {"not_null": "not_null", "unique": "unique"}


def _rewrite_refs(sql: str, assets: list[Asset]) -> str:
    """`from staging.stg_games` -> `from {{ ref('stg_games') }}` for every known model."""
    out = sql
    for other in assets:
        pattern = re.compile(rf"\b{re.escape(other.name)}\b")
        out = pattern.sub(f"{{{{ ref('{other.model}') }}}}", out)
    return out


def _absolutize_runtime_paths(sql: str, repo_root: Path) -> str:
    """`read_parquet('.run/…')` -> an absolute path.

    Spec SQL carries repo-relative runtime paths. That works for the SQLMesh target (run from
    the repo root) but NOT for dbt: Dagster/dbt execute from the dbt project directory, so a
    relative path silently resolves to the wrong place and the model reads nothing.
    """
    return sql.replace("'.run/", f"'{repo_root}/.run/")


def _model_sql(asset: Asset, assets: list[Asset], repo_root: Path) -> str:
    materialized = _MATERIALIZATION.get(asset.materialization, "table")
    # `cast` rather than bare isinstance narrowing: YAML gives Any, and pyright strict rejects
    # the resulting list[Unknown] element types.
    tags_value = asset.meta.get("tags")
    tag_list = (
        [str(t) for t in cast("list[Any]", tags_value)] if isinstance(tags_value, list) else []
    )
    config = f"{{{{ config(materialized='{materialized}', tags={tag_list!r}) }}}}"
    body = _absolutize_runtime_paths(_rewrite_refs(asset.sql, assets), repo_root)
    return f"{config}\n\n{body}\n"


def _schema_yml(assets: list[Asset]) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    for asset in assets:
        columns_value = asset.meta.get("columns")
        columns_meta = cast("list[Any]", columns_value) if isinstance(columns_value, list) else []
        columns: list[dict[str, Any]] = []
        for col_value in columns_meta:
            if not isinstance(col_value, dict):
                continue
            col = cast("dict[str, Any]", col_value)
            checks_value = col.get("checks")
            checks = cast("list[Any]", checks_value) if isinstance(checks_value, list) else []
            tests = [
                _TEST[str(cast("dict[str, Any]", c)["name"])]
                for c in checks
                if isinstance(c, dict) and cast("dict[str, Any]", c).get("name") in _TEST
            ]
            entry: dict[str, Any] = {"name": str(col.get("name"))}
            if col.get("description"):
                entry["description"] = str(col["description"])
            if tests:
                entry["data_tests"] = tests
            columns.append(entry)
        model: dict[str, Any] = {"name": asset.model}
        if asset.meta.get("description"):
            model["description"] = str(asset.meta["description"])
        if columns:
            model["columns"] = columns
        models.append(model)
    return {"version": 2, "models": models}


def compile_to_dbt(
    spec_sql_dir: Path, project_dir: Path, *, warehouse: Path, repo_root: Path
) -> list[str]:
    """Generate a runnable dbt (duckdb) project from `spec/sql`; return model names."""
    assets = load_assets(spec_sql_dir)
    models_dir = project_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    for stale in models_dir.rglob("*"):
        if stale.is_file():
            stale.unlink()

    for asset in assets:
        target = models_dir / asset.schema / f"{asset.model}.sql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_model_sql(asset, assets, repo_root), encoding="utf-8")

    (models_dir / "schema.yml").write_text(
        yaml.safe_dump(_schema_yml(assets), sort_keys=False), encoding="utf-8"
    )
    (project_dir / "dbt_project.yml").write_text(
        yaml.safe_dump(
            {
                "name": "ogip",
                "version": "0.1.0",
                "profile": "ogip",
                "model-paths": ["models"],
                "models": {"ogip": {"+materialized": "table"}},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "profiles.yml").write_text(
        yaml.safe_dump(
            {
                "ogip": {
                    "target": "dev",
                    "outputs": {"dev": {"type": "duckdb", "path": str(warehouse), "threads": 4}},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return [asset.name for asset in assets]
