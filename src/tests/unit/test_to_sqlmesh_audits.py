"""`@bruin` checks must survive compilation as SQLMesh audits (ODTS §5).

Today `to_sqlmesh._model_text` renders only `MODEL(name, kind)` and silently drops
`columns.checks` / top-level `checks`. These tests pin the fix: known checks become
audits in the emitted `MODEL(...)` block, and an unknown check name is a hard compile
error rather than a silent skip.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlmesh.core.audit import builtin
from sqlmesh.core.audit.definition import ModelAudit

from ogip.spec_compile import compile_to_sqlmesh
from ogip.spec_compile.dialect import SqlSpecError

REPO = Path(__file__).resolve().parents[3]
SPEC_SQL = REPO / "spec" / "sql"


def test_checks_become_sqlmesh_audits(tmp_path: Path) -> None:
    compile_to_sqlmesh(SPEC_SQL, tmp_path / "models")
    core = (tmp_path / "models" / "core" / "game.sql").read_text()
    assert "not_null(columns := (game_sk))" in core
    assert "unique_values(columns := (game_sk))" in core
    critic = (tmp_path / "models" / "core" / "critic_reception.sql").read_text()
    assert "accepted_range(column := metacritic_score, min_v := 0, max_v := 100)" in critic
    pricing = (tmp_path / "models" / "core" / "console_pricing.sql").read_text()
    assert "unique_combination_of_columns(columns := (game_sk, locale))" in pricing


def test_unknown_check_name_fails_compilation(tmp_path: Path) -> None:
    bad = tmp_path / "spec"
    (bad / "core").mkdir(parents=True)
    (bad / "core" / "x.sql").write_text(
        "/* @bruin\nname: core.x\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n  - name: a\n    checks: [{name: teleport}]\n@bruin */\nselect 1 as a\n"
    )
    with pytest.raises(SqlSpecError):
        compile_to_sqlmesh(bad, tmp_path / "out")


def test_no_audits_block_when_asset_has_no_checks(tmp_path: Path) -> None:
    """Models without checks stay byte-identical to today (no empty `audits ()` noise)."""
    spec = tmp_path / "spec"
    (spec / "zz").mkdir(parents=True)
    (spec / "zz" / "plain.sql").write_text(
        "/* @bruin\nname: zz.plain\ntype: duckdb.sql\nmaterialization: {type: view}\n@bruin */\n"
        "select 1 as id\n"
    )
    compile_to_sqlmesh(spec, tmp_path / "models")
    text = (tmp_path / "models" / "zz" / "plain.sql").read_text()
    assert "audits" not in text
    assert text == "MODEL (\n  name zz.plain,\n  kind VIEW\n);\n\nselect 1 as id\n"


def test_emitted_audits_are_all_builtin_names(tmp_path: Path) -> None:
    known = {a.name for a in vars(builtin).values() if isinstance(a, ModelAudit)}
    compile_to_sqlmesh(SPEC_SQL, tmp_path / "models")
    for f in (tmp_path / "models").rglob("*.sql"):
        for name in re.findall(r"^\s{4}([a-z_]+)\(", f.read_text(), re.M):
            assert name in known, f"{f.name}: emitted audit {name!r} is not a sqlmesh built-in"
