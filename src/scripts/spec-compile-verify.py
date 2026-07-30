#!/usr/bin/env python
"""Cross-engine parity gate — the claim `docs/comparisons/*` rests on, made executable.

Every transform setup is generated from the one `spec/sql`; this asserts they therefore
produce the **same data**. It regenerates each engine's project, builds it into its own
isolated scratch warehouse from the shared raw fixture, and diffs the result against the
plain-SQL runner (the framework-free reference). A mismatch means an engine's generator
drifted from the spec — a compile bug, not a data bug.

`plain_sql` and the AST layer are pure-Python (always run). `dbt` and `bruin` need their
tooling (`--group engines` / the `bruin` CLI) and are opt-out via flags. Native SQLMesh and
SQLMesh-over-dbt manage their own gateway/state DB and are exercised by the production flow
and `transform/engines.py`, not duplicated here.

Usage::

    just spec-verify                 # plain_sql + dbt + bruin
    uv run python src/scripts/spec-compile-verify.py --no-dbt --no-bruin   # AST + plain_sql only
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import duckdb

Row = tuple[object, ...]

REPO = Path(__file__).resolve().parents[2]
SPEC_SQL = REPO / "spec" / "sql"
RAW_FIXTURE = REPO / ".run" / "data" / "raw" / "rawg__games"
# The relation every engine must agree on, ordered so row-by-row equality is meaningful.
PARITY_QUERY = "select game_sk, round(popularity_score, 6) from fs.market_features order by game_sk"


class ParityError(RuntimeError):
    """An engine's output diverged from the plain-SQL reference."""


def _rows(warehouse: Path) -> list[Row]:
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        return con.execute(PARITY_QUERY).fetchall()
    finally:
        con.close()


def _build_plain_sql(_scratch: Path, warehouse: Path) -> list[Row]:
    from transform.runner import run_plain_sql

    run_plain_sql(SPEC_SQL, warehouse)
    return _rows(warehouse)


def _build_dbt(scratch: Path, warehouse: Path) -> list[Row]:
    from ogip.spec_compile import compile_to_dbt

    project = scratch / "dbt"
    compile_to_dbt(SPEC_SQL, project, warehouse=warehouse, repo_root=REPO)
    where = ["--project-dir", str(project), "--profiles-dir", str(project)]
    base = ["uv", "run", "--group", "engines", "dbt"]
    subprocess.run([*base, "deps", *where], check=True, cwd=REPO)
    subprocess.run([*base, "build", *where], check=True, cwd=REPO)
    return _rows(warehouse)


def _build_opendbt(scratch: Path, warehouse: Path) -> list[Row]:
    from ogip.spec_compile import compile_to_dbt

    project = scratch / "opendbt"
    # No hub packages: OpenDBT pins dbt <1.10, where the versions we track refuse to install.
    compile_to_dbt(SPEC_SQL, project, warehouse=warehouse, repo_root=REPO, with_packages=False)
    program = (
        "from pathlib import Path;from opendbt import OpenDbtProject;"
        "import sys;p=Path(sys.argv[1]);"
        "OpenDbtProject(project_dir=p,profiles_dir=p,target='dev').run('build')"
    )
    subprocess.run(
        ["uv", "run", "--group", "opendbt", "python", "-c", program, str(project)],
        check=True,
        cwd=REPO,
    )
    return _rows(warehouse)


def _build_bruin(scratch: Path, warehouse: Path) -> list[Row]:
    from ogip.spec_compile import compile_to_bruin

    project = scratch / "bruin"
    compile_to_bruin(SPEC_SQL, project, warehouse=warehouse)
    if shutil.which("bruin") is None:
        raise ParityError("bruin CLI not on PATH — install it or pass --no-bruin")
    subprocess.run(
        ["bruin", "run", "--config-file", str(project / ".bruin.yml"), str(project)],
        check=True,
        cwd=REPO,
        env={**os.environ, "TELEMETRY_OPTOUT": "true"},
    )
    return _rows(warehouse)


Builder = Callable[[Path, Path], list[Row]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spec-compile-verify", description=__doc__)
    parser.add_argument("--no-dbt", action="store_true", help="skip the dbt engine")
    parser.add_argument("--no-opendbt", action="store_true", help="skip the OpenDBT engine")
    parser.add_argument("--no-bruin", action="store_true", help="skip the Bruin engine")
    args = parser.parse_args(argv)

    if not any(RAW_FIXTURE.glob("*.parquet")):
        print(f"[verify] no raw fixture under {RAW_FIXTURE} — run the pipeline once first")
        return 2

    sys.path.insert(0, str(REPO))  # `transform`/`ingestion` are repo-root packages
    engines: list[tuple[str, Builder]] = [
        ("dbt", _build_dbt),
        ("opendbt", _build_opendbt),
        ("bruin", _build_bruin),
    ]
    skip = {"dbt": args.no_dbt, "opendbt": args.no_opendbt, "bruin": args.no_bruin}

    # Scratch lives under .run/ (gitignored) rather than the system temp dir: Bruin walks up
    # for a git root and refuses to run outside one, and it resolves a project-relative
    # warehouse path — an absolute path inside the repo tree satisfies both.
    tmp_root = REPO / ".run" / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="parity-", dir=tmp_root) as tmp:
        scratch = Path(tmp)
        reference = _build_plain_sql(scratch, scratch / "plain_sql.duckdb")
        print(f"[verify] plain_sql (reference): {len(reference)} rows")

        mismatches: list[str] = []
        for name, builder in engines:
            if skip[name]:
                print(f"[verify] {name}: SKIPPED")
                continue
            warehouse = scratch / f"{name}.duckdb"
            rows = builder(scratch, warehouse)
            ok = rows == reference
            print(f"[verify] {name}: {len(rows)} rows — {'OK' if ok else 'MISMATCH'}")
            if not ok:
                mismatches.append(name)

    if mismatches:
        print(f"[verify] FAIL — diverged from plain_sql: {', '.join(mismatches)}")
        return 1
    print("[verify] PASS — every engine agrees with the plain-SQL reference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
