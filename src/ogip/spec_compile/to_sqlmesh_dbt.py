"""SQLMesh-over-dbt (profile `prefect-sqlmesh-over-dbt`): the generated dbt project plus a
``config.py`` for SQLMesh's native dbt loader. The comparison this enables: what SQLMesh's
plan/state machinery adds on top of an unchanged dbt-format project.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

import yaml

from .to_dbt import compile_to_dbt

# SQLMesh needs a finite backfill start for dbt models; keep in step with the native
# project's `model_defaults.start` (transform/sqlmesh/config.yaml).
_START = "2020-01-01"

_CONFIG = '''"""GENERATED from spec/ — SQLMesh dbt-loader entry point (do not hand-edit).

SQLMesh state lives OUTSIDE the warehouse (its own DuckDB file) so the shared warehouse
stays engine-clean — the same isolation OGAP settled on (ADR-006 there).
"""

from pathlib import Path

from sqlmesh.core.config import DuckDBConnectionConfig
from sqlmesh.dbt.loader import sqlmesh_config

_WAREHOUSE = Path(__file__).resolve().parents[2] / ".run" / "data" / "warehouse"
_WAREHOUSE.mkdir(parents=True, exist_ok=True)  # DuckDB does not create missing dirs
_STATE = _WAREHOUSE / "sqlmesh_dbt_state.duckdb"

config = sqlmesh_config(
    Path(__file__).parent,
    state_connection=DuckDBConnectionConfig(database=str(_STATE)),
)
'''

_README = """# `transform/sqlmesh_dbt/` — GENERATED from `spec/` (do not hand-edit)

The `prefect-sqlmesh-over-dbt` profile: the same generated dbt project as `transform/dbt/`,
plus `config.py` so SQLMesh loads it natively. Regenerate: `just spec-compile sqlmesh-dbt`.
Run from the repo root: `uv run --group engines sqlmesh -p transform/sqlmesh_dbt plan`.
"""


def compile_to_sqlmesh_over_dbt(
    spec_sql_dir: Path, project_dir: Path, *, warehouse: Path, repo_root: Path
) -> list[str]:
    """Generate a dbt project + SQLMesh dbt-loader config; return model names."""
    names = compile_to_dbt(spec_sql_dir, project_dir, warehouse=warehouse, repo_root=repo_root)
    project_yml = project_dir / "dbt_project.yml"
    project = cast("dict[str, Any]", yaml.safe_load(project_yml.read_text(encoding="utf-8")))
    project["models"]["+start"] = _START  # SQLMesh's dbt loader checks the top-level block
    project_yml.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    # No dbt-hub packages in THIS flavor: introspection packages (dbt_project_evaluator)
    # need dbt-runtime jinja (`graph`, run hooks) that SQLMesh's loader cannot render, and
    # the SQLMesh-over-dbt comparison targets our models, not dbt tooling. No `dbt deps`
    # step needed as a result.
    (project_dir / "packages.yml").write_text(yaml.safe_dump({"packages": []}), encoding="utf-8")
    shutil.rmtree(project_dir / "dbt_packages", ignore_errors=True)
    (project_dir / "config.py").write_text(_CONFIG, encoding="utf-8")
    (project_dir / "README.md").write_text(_README, encoding="utf-8")
    return names
