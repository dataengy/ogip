"""Drift guard: every committed engine snapshot must cover every `spec/sql` model.

`transform/{dbt,opendbt,sqlmesh_dbt,bruin}` are regenerated from `spec/sql` by
`uv run python -m ogip.spec_compile all` (see `src/ogip/spec_compile/__main__.py`) and then
committed as reviewable snapshots. Nothing re-runs the compiler automatically, so a `spec/sql`
change (new source, new model) can silently leave the snapshots stale — this test is the tripwire.
Regenerate with `just spec-compile` (or the command above) whenever it fails.

`transform/sqlmesh/models/` is deliberately excluded from that list: it is `.gitignore`d
(since M0, "generated models... spec/ is the SSoT") because SQLMesh is the production engine
and recompiles fresh immediately before every real run (`pipelines/_shared/steps.py::
build_warehouse`) — there is no committed snapshot for it to drift. It gets its own guard below
that exercises the live compiler instead of a checked-in directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ogip.spec_compile import compile_to_sqlmesh, load_assets

_REPO = Path(__file__).resolve().parents[3]
_SPEC_SQL = _REPO / "spec" / "sql"

_COMMITTED_ENGINE_ROOTS = (
    "transform/sqlmesh_dbt/models",
    "transform/dbt/models",
    "transform/opendbt/models",
    "transform/bruin/assets",
)


def _spec_model_stems() -> set[str]:
    return {f"{asset.schema}/{asset.model}" for asset in load_assets(_SPEC_SQL)}


def _stems(root: Path) -> set[str]:
    return {f"{p.parent.name}/{p.stem}" for p in root.rglob("*.sql")}


@pytest.mark.parametrize("engine_root", _COMMITTED_ENGINE_ROOTS)
def test_engine_snapshot_covers_every_spec_model(engine_root: str) -> None:
    root = _REPO / engine_root
    assert root.is_dir(), f"{root} missing — run `just spec-compile`"
    missing = _spec_model_stems() - _stems(root)
    assert not missing, (
        f"{engine_root} is missing models {sorted(missing)} — regenerate with "
        "`export UV_PROJECT_ENVIRONMENT=.run/venv && uv run python -m ogip.spec_compile all`"
    )


def test_sqlmesh_compiler_covers_every_spec_model(tmp_path: Path) -> None:
    """No committed snapshot to check (see module docstring) — guard the compiler itself."""
    models_dir = tmp_path / "models"
    compile_to_sqlmesh(_SPEC_SQL, models_dir)
    missing = _spec_model_stems() - _stems(models_dir)
    assert not missing, f"compile_to_sqlmesh is missing models {sorted(missing)}"
