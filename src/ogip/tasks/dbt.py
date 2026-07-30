"""dbt tasks — regenerate the project from `spec/`, then invoke dbt.

Regeneration is implicit and unconditional: `spec/` is the SSoT (ADR-0005) and the dbt project
is generated, never hand-edited, so a caller that had to *ask* for regeneration would be
asserting a fact the system already owns.

These tasks deliberately do NOT ensure raw data exists. A build that silently ingests is a
hidden edge in the dependency graph; ingestion is `ingest.rawg`, composed ahead of the build by
whoever needs it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, cast

import yaml

from ogip.config import get_settings
from ogip.logger import log
from ogip.spec_compile.to_dbt import compile_to_dbt
from ogip.tasks._registry import odos_task

__all__ = ["dbt_build", "dbt_command", "dbt_deps", "dbt_parse"]

_REPO = Path(__file__).resolve().parents[3]
_SPEC_SQL = _REPO / "spec" / "sql"


def dbt_command(project_dir: Path, verb: str, *flags: str) -> list[str]:
    """Build the dbt argv. `--project-dir`/`--profiles-dir` must follow the subcommand."""
    return [
        "uv",
        "run",
        "--group",
        "engines",
        "dbt",
        verb,
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(project_dir),
        *flags,
    ]


def _regenerate(project_dir: Path) -> list[str]:
    # repo_root=Path() keeps runtime paths as './.run/…' — identical to the committed CLI
    # render (spec_compile.__main__). Correct because `_run` executes dbt with cwd=_REPO, and
    # essential because the project is TRACKED: an absolute repo_root here rewrote the models
    # with this machine's private checkout path on every run (leaked in 4 committed files).
    models = compile_to_dbt(
        _SPEC_SQL,
        project_dir,
        warehouse=get_settings().platform.warehouse_path,
        repo_root=Path(),
    )
    log.info("regenerated {n} dbt models from spec/ into {p}", n=len(models), p=project_dir)
    return models


def _run(project_dir: Path, verb: str, *flags: str) -> None:
    argv = dbt_command(project_dir, verb, *flags)
    log.bind(task=f"dbt.{verb}").info("exec: {c}", c=" ".join(argv))
    subprocess.run(argv, check=True, cwd=_REPO)


def _deps_incomplete(project_dir: Path) -> bool:
    """True when hub packages are missing OR only half-installed.

    Completeness, not mere existence: an interrupted `dbt deps` (Ctrl-C, killed process,
    dropped network) leaves `dbt_packages/` present but half-populated — a bare `is_dir()`
    passed on that, so deps were never repaired and every later dbt command died with
    "found N package(s) in packages.yml, but only M package(s) installed". Transitive deps
    only ADD directories, so `installed < declared` is the reliable "incomplete" test.
    """
    pkg_dir = project_dir / "dbt_packages"
    if not pkg_dir.is_dir():
        return True
    packages_yml = project_dir / "packages.yml"
    declared = 0
    if packages_yml.is_file():
        raw = yaml.safe_load(packages_yml.read_text(encoding="utf-8"))
        pkgs = cast("dict[str, Any]", raw).get("packages") if isinstance(raw, dict) else None
        declared = len(cast("list[Any]", pkgs)) if isinstance(pkgs, list) else 0
    installed = sum(1 for p in pkg_dir.iterdir() if p.is_dir())
    return installed < declared


@odos_task("dbt.deps")
def dbt_deps(*, project_dir: Path, force: bool = False) -> None:
    """Install hub packages.

    Two distinct behaviours, inherited from the original bash split between the standalone
    `dbt-deps` task and the internal `ensure_deps()` helper it shared with build/evaluate:
    `force=True` runs `dbt deps` unconditionally — this is what a caller wants after editing
    `packages.yml`, where a gated check would silently no-op on a stale cache. `force=False`
    (the default, used by `dbt_parse`/`dbt_build`) skips only when the install is COMPLETE
    (see `_deps_incomplete`), since dbt caches into `<project>/dbt_packages/` and a build
    shouldn't pay the network cost every time.
    """
    _regenerate(project_dir)
    if force or _deps_incomplete(project_dir):
        _run(project_dir, "deps")


@odos_task("dbt.parse")
def dbt_parse(*, project_dir: Path) -> None:
    """Refresh the manifest without running any model."""
    dbt_deps(project_dir=project_dir)
    _run(project_dir, "parse")


@odos_task("dbt.build")
def dbt_build(
    *,
    project_dir: Path,
    full_refresh: bool = False,
    select: str | None = None,
    state: str | None = None,
) -> None:
    """Run models + tests. The flag matrix that used to be six separate bash tasks."""
    dbt_deps(project_dir=project_dir)
    flags: list[str] = []
    if full_refresh:
        flags.append("--full-refresh")
    if select is not None:
        flags += ["--select", select]
    if state is not None:
        flags += ["--state", state]
    _run(project_dir, "build", *flags)
