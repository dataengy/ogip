"""Render parsed Bruin assets into SQLMesh model files.

SQLMesh infers dependencies from the SQL (`FROM schema.model`), so the Bruin `depends` stays
documentation; we translate `name` + materialization into a `MODEL(...)` block, plus (ODTS
§5-6) project every authored `@bruin` `checks:` entry into a SQLMesh audit - the DQ vocabulary
is portable across engines, so the check MUST survive the compile or the constraint is lost
silently. An unknown check name is a compile-time error (ODTS §5: "attributes outside the
check vocabulary MUST fail compilation"), never a silent skip.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from .bruin import Asset, load_assets
from .dialect import SqlSpecError

_KIND = {"table": "FULL", "view": "VIEW"}


def _audit_for(model: str, col: str, chk: dict[str, Any]) -> str:
    """One `@bruin` check -> one SQLMesh audit call. Raises on an unknown check name."""
    name = chk.get("name")
    if name == "not_null":
        return f"not_null(columns := ({col}))"
    if name == "unique":
        return f"unique_values(columns := ({col}))"
    if name == "non_negative":
        return f"accepted_range(column := {col}, min_v := 0)"
    if name == "between":
        lo, hi = chk["args"]
        return f"accepted_range(column := {col}, min_v := {lo}, max_v := {hi})"
    if name == "accepted_values":
        values = ", ".join(f"'{v}'" for v in chk["args"])
        return f"accepted_values(column := {col}, is_in := ({values}))"
    raise SqlSpecError(f"{model}: column {col!r} has unknown check {name!r}")


def _audits(asset: Asset) -> list[str]:
    """Every audit this asset's `@bruin` checks project to, in declaration order."""
    audits: list[str] = []
    for column in cast("list[dict[str, Any]]", asset.meta.get("columns") or []):
        col = str(column["name"])
        for chk in cast("list[dict[str, Any]]", column.get("checks") or []):
            audits.append(_audit_for(asset.name, col, chk))
    for chk in cast("list[dict[str, Any]]", asset.meta.get("checks") or []):
        name = chk.get("name")
        if name == "unique" and "columns" in chk:
            cols = ", ".join(str(c) for c in chk["columns"])
            audits.append(f"unique_combination_of_columns(columns := ({cols}))")
        else:
            # the only top-level (cross-column) check the ODTS vocabulary defines is a
            # composite `unique` over `columns:` - anything else at this level is unknown.
            raise SqlSpecError(f"{asset.name}: unknown top-level check {name!r}")
    return audits


def _model_text(asset: Asset) -> str:
    kind = _KIND.get(asset.materialization, "FULL")
    audits = _audits(asset)
    if audits:
        audit_lines = ",\n    ".join(audits)
        header = (
            f"MODEL (\n  name {asset.name},\n  kind {kind},\n"
            f"  audits (\n    {audit_lines}\n  )\n);\n\n"
        )
    else:
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
