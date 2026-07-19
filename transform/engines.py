"""Comparison-engine launcher (A12): build the warehouse with a non-default engine.

Production is SQLMesh only (AGENTS.md — the production path is sacred); these run the SAME
`spec/` through the alternatives so `docs/comparisons/*` measures real runs, not readings.
Each engine project is regenerated from `spec/` immediately before the run — a stale
checkout can never drift from the SSoT. dbt-based engines resolve their optional deps via
`uv run --group engines`; Bruin needs the `bruin` CLI on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from transform.runner import run_plain_sql

from ogip.config import get_settings
from ogip.logger import logger
from ogip.spec_compile import compile_to_bruin, compile_to_dbt, compile_to_sqlmesh_over_dbt

COMPARISON_ENGINES = ("plain_sql", "dbt", "opendbt", "sqlmesh_dbt", "bruin")

_REPO = Path(__file__).resolve().parents[1]
_SPEC_SQL = _REPO / "spec" / "sql"
_TRANSFORM = _REPO / "transform"
# Generated projects carry repo-relative paths (they are committed), so every engine runs
# with cwd at the repo root; repo_root=Path() keeps the generated SQL machine-independent.
_REL_ROOT = Path()


def _run(cmd: list[str], *, engine: str) -> None:
    logger.bind(engine=engine).info("exec: {c}", c=" ".join(cmd))
    subprocess.run(cmd, check=True, cwd=_REPO)


def _run_dbt(project: Path, engine: str) -> None:
    where = ["--project-dir", str(project), "--profiles-dir", str(project)]
    if not (project / "dbt_packages").exists():  # `dbt deps` is idempotent but slow — once
        _run(["uv", "run", "--group", "engines", "dbt", "deps", *where], engine=engine)
    _run(["uv", "run", "--group", "engines", "dbt", "build", *where], engine=engine)


# OpenDBT has no console script — it is driven through its Python API, so the runner is a
# `-c` program rather than a CLI call.
_OPENDBT_PROGRAM = """
import sys
from pathlib import Path
from opendbt import OpenDbtProject

project = Path(sys.argv[1])
OpenDbtProject(project_dir=project, profiles_dir=project, target="dev").run("build")
"""


def _run_opendbt(project: Path, engine: str) -> None:
    # `--group opendbt`, not `engines`: OpenDBT patches dbt internals and supports dbt <1.10,
    # so it resolves its own dbt (declared conflicting in pyproject) rather than sharing one.
    # The project carries no hub packages, so there is no `dbt deps` step.
    _run(
        ["uv", "run", "--group", "opendbt", "python", "-c", _OPENDBT_PROGRAM, str(project)],
        engine=engine,
    )


def run_transform_engine(engine: str) -> list[str]:
    """Regenerate the engine's project from `spec/`, run it, return built model names."""
    warehouse = get_settings().platform.warehouse_path
    if engine == "plain_sql":
        return run_plain_sql()
    if engine == "dbt":
        project = _TRANSFORM / "dbt"
        names = compile_to_dbt(_SPEC_SQL, project, warehouse=warehouse, repo_root=_REL_ROOT)
        _run_dbt(project, engine)
        return names
    if engine == "opendbt":
        # OpenDBT is dbt-core *extended* (python/dlt models, mesh refs, custom adapters) — the
        # same models, a different runtime. It gets its own project only because it pins
        # dbt <1.10, where the hub package set we track refuses to install.
        project = _TRANSFORM / "opendbt"
        names = compile_to_dbt(
            _SPEC_SQL, project, warehouse=warehouse, repo_root=_REL_ROOT, with_packages=False
        )
        _run_opendbt(project, engine)
        return names
    if engine == "sqlmesh_dbt":
        project = _TRANSFORM / "sqlmesh_dbt"
        names = compile_to_sqlmesh_over_dbt(
            _SPEC_SQL, project, warehouse=warehouse, repo_root=_REL_ROOT
        )
        sqlmesh = ["uv", "run", "--group", "engines", "sqlmesh", "-p", str(project)]
        _run([*sqlmesh, "plan", "--auto-apply", "--no-prompts"], engine=engine)
        return names
    if engine == "bruin":
        names = compile_to_bruin(_SPEC_SQL, _TRANSFORM / "bruin", warehouse=warehouse)
        if shutil.which("bruin") is None:
            raise RuntimeError(
                "the `prefect-bruin` profile needs the Bruin CLI on PATH — "
                "install: https://getbruin.com (curl installer or homebrew)"
            )
        # --config-file: .bruin.yml lives IN the generated project — without the flag Bruin
        # would look for it at the git repo root, and the repo root stays lean (AGENTS.md).
        config_file = _TRANSFORM / "bruin" / ".bruin.yml"
        _run(
            ["bruin", "run", "--config-file", str(config_file), str(_TRANSFORM / "bruin")],
            engine=engine,
        )
        return names
    raise ValueError(
        f"unknown transform engine {engine!r} — 'sqlmesh' (production) or {COMPARISON_ENGINES}"
    )
