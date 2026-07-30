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
from sqlmesh.core.dialect import parse as parse_sqlmesh_expressions

# sqlmesh's own signature has a partially-unknown default (`Dict[Pattern[Unknown], str]`),
# which pyright strict propagates onto the import itself, not onto anything we wrote here.
from sqlmesh.core.model import load_sql_based_model  # pyright: ignore[reportUnknownVariableType]

from ogip.spec_compile import compile_to_sqlmesh
from ogip.spec_compile.dialect import SqlSpecError

REPO = Path(__file__).resolve().parents[3]
SPEC_SQL = REPO / "spec" / "sql"


def _write_asset(spec_dir: Path, schema: str, model: str, header: str, sql: str) -> None:
    """Write one synthetic Bruin asset (schema/model.sql) under ``spec_dir``."""
    target = spec_dir / schema / f"{model}.sql"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"/* @bruin\n{header}\n@bruin */\n{sql}\n")


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


def test_generated_models_load_via_real_sqlmesh_parser(tmp_path: Path) -> None:
    """Pin MODEL-block validity against SQLMesh's own parser, not just the name-floor regex.

    Replicates the manual check from `task-2a-report.md`: feed the generated model text
    through `sqlmesh.core.dialect.parse` + `sqlmesh.core.model.load_sql_based_model` (the
    same path SQLMesh itself uses to load a project) and assert it loads without a parse
    error AND that the audits SQLMesh extracts match what we emitted — so a future
    formatting regression (bad indent/comma in the `audits (...)` block) fails loudly here
    instead of only at `sqlmesh plan` time.
    """
    compile_to_sqlmesh(SPEC_SQL, tmp_path / "models")

    game_path = tmp_path / "models" / "core" / "game.sql"
    game_expressions = parse_sqlmesh_expressions(game_path.read_text(), default_dialect="duckdb")
    game_model = load_sql_based_model(game_expressions, dialect="duckdb", path=game_path)
    assert game_model.name == "core.game"
    # game_sk contributes not_null/unique_values; the Part 2b `metacritic` between-check
    # (core.game.metacritic is a 0-100 score column) adds accepted_range.
    assert {name for name, _ in game_model.audits} == {
        "not_null",
        "unique_values",
        "accepted_range",
    }

    pricing_path = tmp_path / "models" / "core" / "console_pricing.sql"
    pricing_expressions = parse_sqlmesh_expressions(
        pricing_path.read_text(), default_dialect="duckdb"
    )
    pricing_model = load_sql_based_model(pricing_expressions, dialect="duckdb", path=pricing_path)
    assert pricing_model.name == "core.console_pricing"
    pricing_audit_names = {name for name, _ in pricing_model.audits}
    assert "unique_combination_of_columns" in pricing_audit_names
    assert "accepted_range" in pricing_audit_names


def test_between_check_missing_args_raises_sqlspec_error(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "core",
        "x",
        "name: core.x\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n  - name: a\n    checks: [{name: between}]",
        "select 1 as a",
    )
    with pytest.raises(SqlSpecError, match=r"'between' needs args \[min, max\]"):
        compile_to_sqlmesh(spec, tmp_path / "out")


def test_accepted_values_check_empty_args_raises_sqlspec_error(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "core",
        "x",
        "name: core.x\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n  - name: a\n    checks: [{name: accepted_values, args: []}]",
        "select 1 as a",
    )
    with pytest.raises(SqlSpecError, match=r"'accepted_values' needs args"):
        compile_to_sqlmesh(spec, tmp_path / "out")


def test_top_level_check_other_than_unique_raises_sqlspec_error(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "core",
        "x",
        "name: core.x\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "checks:\n  - name: not_null",
        "select 1 as a",
    )
    with pytest.raises(SqlSpecError, match="unknown top-level check"):
        compile_to_sqlmesh(spec, tmp_path / "out")


def test_top_level_unique_without_columns_raises_sqlspec_error(tmp_path: Path) -> None:
    """The message must point at the fix (`columns:` missing), not claim `unique` is unknown."""
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "core",
        "x",
        "name: core.x\ntype: duckdb.sql\nmaterialization: {type: table}\nchecks:\n  - name: unique",
        "select 1 as a",
    )
    with pytest.raises(SqlSpecError, match="requires a 'columns:' list"):
        compile_to_sqlmesh(spec, tmp_path / "out")


def test_dbt_only_column_check_is_skipped_not_raised(tmp_path: Path) -> None:
    """`relationships` is dbt-native; SQLMesh has no builtin for it, so it is SKIPPED.

    Re-root (#40/#34): dbt becomes a primary engine and authors richer DQ in `spec/sql`.
    SQLMesh must compile such a model instead of dying on it — but ONLY for names on the
    explicit dbt-only allowlist, so a genuine typo still fails loud (ODTS §5).
    """
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "fs",
        "x",
        "name: fs.x\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n  - name: game_sk\n    checks:\n"
        "      - {name: not_null}\n"
        "      - {name: relationships, value: {to: game, field: game_sk}}",
        "select 1 as game_sk",
    )
    compile_to_sqlmesh(spec, tmp_path / "out")
    text = (tmp_path / "out" / "fs" / "x.sql").read_text()
    assert "not_null(columns := (game_sk))" in text  # native check still projected
    assert "relationships" not in text  # dbt-only check skipped, not emitted


def test_dbt_only_top_level_check_is_skipped_not_raised(tmp_path: Path) -> None:
    """Asset-level `not_empty` is dbt-only — skipped, and must not break the MODEL block."""
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "fs",
        "y",
        "name: fs.y\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "checks:\n  - {name: not_empty}",
        "select 1 as a",
    )
    compile_to_sqlmesh(spec, tmp_path / "out")
    text = (tmp_path / "out" / "fs" / "y.sql").read_text()
    assert "not_empty" not in text
    assert "audits" not in text  # nothing native left → no empty audits() noise


def test_accepted_range_value_form_becomes_audit(tmp_path: Path) -> None:
    """#34 authors `accepted_range` as `value: {min, max}` — a different shape from `between`."""
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "fs",
        "z",
        "name: fs.z\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n  - name: critic_score\n"
        "    checks: [{name: accepted_range, value: {min: 0, max: 1}}]",
        "select 0.5 as critic_score",
    )
    compile_to_sqlmesh(spec, tmp_path / "out")
    text = (tmp_path / "out" / "fs" / "z.sql").read_text()
    assert "accepted_range(column := critic_score, min_v := 0, max_v := 1)" in text


def test_typo_check_still_fails_loud_after_allowlist(tmp_path: Path) -> None:
    """The dbt-only allowlist must NOT degrade into 'skip anything unrecognized'."""
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "fs",
        "w",
        "name: fs.w\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n  - name: a\n    checks: [{name: relationshipz}]",
        "select 1 as a",
    )
    with pytest.raises(SqlSpecError, match="unknown check"):
        compile_to_sqlmesh(spec, tmp_path / "out")


def test_accepted_values_check_becomes_sqlmesh_audit(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "core",
        "x",
        "name: core.x\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n  - name: region\n    checks: [{name: accepted_values, args: [a, b]}]",
        "select 'a' as region",
    )
    compile_to_sqlmesh(spec, tmp_path / "out")
    text = (tmp_path / "out" / "core" / "x.sql").read_text()
    assert "accepted_values(column := region, is_in := ('a', 'b'))" in text
