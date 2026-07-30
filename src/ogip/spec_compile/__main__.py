"""Regenerate `transform/` engine projects from `spec/` (ADR-0005).

`just spec-compile [engine]` / `uv run python -m ogip.spec_compile [engine]`. Engines:
sqlmesh (production) · dbt · sqlmesh-dbt · bruin · all (default). The plain-SQL profile has
no generated project — `transform/runner.py` consumes `spec/sql` directly. Everything is
emitted with repo-relative paths, so generate (and run engines) from the repo root.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ogip.config import get_settings
from ogip.logger import log

from .to_bruin import compile_to_bruin
from .to_dbt import compile_to_dbt
from .to_sqlmesh import compile_to_sqlmesh
from .to_sqlmesh_dbt import compile_to_sqlmesh_over_dbt

ENGINES = ("sqlmesh", "dbt", "opendbt", "sqlmesh-dbt", "bruin")

_REPO = Path(__file__).resolve().parents[3]
_SPEC_SQL = _REPO / "spec" / "sql"


def _generate(engine: str, out: Path, warehouse: Path) -> list[str]:
    # repo_root=Path() renders runtime paths as './.run/…' — the generated projects are
    # committed, so they must stay machine-independent; every engine runs from the repo root.
    rel_root = Path()
    if engine == "sqlmesh":
        return compile_to_sqlmesh(_SPEC_SQL, out / "sqlmesh" / "models")
    if engine == "dbt":
        return compile_to_dbt(_SPEC_SQL, out / "dbt", warehouse=warehouse, repo_root=rel_root)
    if engine == "opendbt":
        # Same models as `dbt`, no hub packages — OpenDBT pins dbt <1.10, where they won't install.
        return compile_to_dbt(
            _SPEC_SQL,
            out / "opendbt",
            warehouse=warehouse,
            repo_root=rel_root,
            with_packages=False,
        )
    if engine == "sqlmesh-dbt":
        return compile_to_sqlmesh_over_dbt(
            _SPEC_SQL, out / "sqlmesh_dbt", warehouse=warehouse, repo_root=rel_root
        )
    if engine == "bruin":
        return compile_to_bruin(_SPEC_SQL, out / "bruin", warehouse=warehouse)
    raise ValueError(f"unknown engine {engine!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ogip.spec_compile", description=__doc__)
    parser.add_argument("engine", nargs="?", default="all", choices=(*ENGINES, "all"))
    parser.add_argument(
        "--out", type=Path, default=_REPO / "transform", help="target root (default: transform/)"
    )
    args = parser.parse_args(argv)
    engine_arg, out = str(args.engine), Path(args.out)
    warehouse = get_settings().platform.warehouse_path  # repo-relative (SSoT: config.yml)
    for engine in ENGINES if engine_arg == "all" else (engine_arg,):
        names = _generate(engine, out, warehouse)
        log.bind(engine=engine).info("generated {n} models: {names}", n=len(names), names=names)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
