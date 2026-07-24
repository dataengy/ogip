"""`@bruin` checks must reach the generated dbt project as real dbt tests (re-root #40).

dbt becomes a PRIMARY engine, so its DQ is no longer decorative: every check authored in
`spec/sql` has to arrive as something `dbt build` actually executes. Before this, `to_dbt`
mapped only `not_null`/`unique` and silently dropped `relationships`, `accepted_range`,
`accepted_values`, `non_negative`, every top-level (cross-column) check, plus `custom_checks`
and `unit_tests` entirely — the exact "constraint lost silently" failure ODTS §5 forbids.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from ogip.spec_compile import compile_to_dbt

REPO = Path(__file__).resolve().parents[3]


def _write_asset(spec_dir: Path, schema: str, model: str, header: str, sql: str) -> None:
    target = spec_dir / schema / f"{model}.sql"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"/* @bruin\n{header}\n@bruin */\n{sql}\n")


def _compile(spec: Path, out: Path) -> dict[str, Any]:
    compile_to_dbt(spec, out, warehouse=out / "wh.duckdb", repo_root=REPO, with_packages=False)
    raw = yaml.safe_load((out / "models" / "schema.yml").read_text())
    return cast("dict[str, Any]", raw)


def _model(schema_yml: dict[str, Any], name: str) -> dict[str, Any]:
    for m in cast("list[dict[str, Any]]", schema_yml["models"]):
        if m["name"] == name:
            return m
    raise AssertionError(f"model {name!r} not in schema.yml")


def _as_dict(value: Any) -> dict[str, Any]:
    """Narrow a YAML-loaded test entry for pyright strict (isinstance gives dict[Unknown, ...])."""
    return cast("dict[str, Any]", value)


def _tests_for(model: dict[str, Any], column: str) -> list[Any]:
    for c in cast("list[dict[str, Any]]", model.get("columns") or []):
        if c["name"] == column:
            return cast("list[Any]", c.get("data_tests") or [])
    raise AssertionError(f"column {column!r} not in model {model['name']!r}")


def test_column_check_vocabulary_becomes_dbt_tests(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "fs",
        "feat",
        "name: fs.feat\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "columns:\n"
        "  - name: game_sk\n"
        "    checks:\n"
        "      - {name: not_null}\n"
        "      - {name: unique}\n"
        "      - {name: relationships, value: {to: game, field: game_sk}}\n"
        "  - name: critic_score\n"
        "    checks: [{name: accepted_range, value: {min: 0, max: 1}}]\n"
        "  - name: revenue\n"
        "    checks: [{name: non_negative}]\n"
        "  - name: region\n"
        "    checks: [{name: accepted_values, args: [eu, us]}]",
        "select 1 as game_sk, 0.5 as critic_score, 1 as revenue, 'eu' as region",
    )
    model = _model(_compile(spec, tmp_path / "out"), "feat")

    game_sk = _tests_for(model, "game_sk")
    assert "not_null" in game_sk
    assert "unique" in game_sk
    rel = [_as_dict(t) for t in game_sk if isinstance(t, dict) and "relationships" in t]
    assert rel, f"relationships test missing: {game_sk}"
    assert rel[0]["relationships"]["to"] == "ref('game')"
    assert rel[0]["relationships"]["field"] == "game_sk"

    rng = [_as_dict(t) for t in _tests_for(model, "critic_score") if isinstance(t, dict)]
    assert rng and rng[0]["dbt_utils.accepted_range"] == {"min_value": 0, "max_value": 1}

    nonneg = [_as_dict(t) for t in _tests_for(model, "revenue") if isinstance(t, dict)]
    assert nonneg and nonneg[0]["dbt_utils.accepted_range"] == {"min_value": 0}

    vals = [_as_dict(t) for t in _tests_for(model, "region") if isinstance(t, dict)]
    assert vals and vals[0]["accepted_values"] == {"values": ["eu", "us"]}


def test_top_level_checks_become_model_level_dbt_tests(tmp_path: Path) -> None:
    """Composite `unique` and asset-level `not_empty` were dropped entirely before."""
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "core",
        "pricing",
        "name: core.pricing\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "checks:\n"
        "  - {name: not_empty}\n"
        "  - name: unique\n    columns: [game_sk, locale]",
        "select 1 as game_sk, 'en-us' as locale",
    )
    model = _model(_compile(spec, tmp_path / "out"), "pricing")
    tests = cast("list[Any]", model.get("data_tests") or [])
    combo = [
        _as_dict(t)
        for t in tests
        if isinstance(t, dict) and "dbt_utils.unique_combination_of_columns" in t
    ]
    assert combo, f"composite unique missing: {tests}"
    assert combo[0]["dbt_utils.unique_combination_of_columns"]["combination_of_columns"] == [
        "game_sk",
        "locale",
    ]
    assert any(
        isinstance(t, dict) and "dbt_expectations.expect_table_row_count_to_be_between" in t
        for t in tests
    ), f"not_empty missing: {tests}"


def test_custom_checks_become_singular_test_files(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "fs",
        "feat",
        "name: fs.feat\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "custom_checks:\n"
        "  - name: popularity_requires_ratings\n"
        "    query: |\n"
        "      select game_sk from fs.feat where score > 0\n",
        "select 1 as game_sk, 1 as score",
    )
    out = tmp_path / "out"
    _compile(spec, out)
    singular = out / "tests" / "popularity_requires_ratings.sql"
    assert singular.is_file(), "custom_checks must become a dbt singular test"
    assert "select game_sk from fs.feat" in singular.read_text()


def test_unit_tests_are_emitted_into_schema_yml(tmp_path: Path) -> None:
    spec = tmp_path / "spec"
    _write_asset(
        spec,
        "fs",
        "feat",
        "name: fs.feat\ntype: duckdb.sql\nmaterialization: {type: table}\n"
        "unit_tests:\n"
        "  - name: score_is_zero_when_rating_is_zero\n"
        "    given:\n"
        "      - input: ref('game')\n"
        "        rows: [{game_sk: a, rating: 0.0}]\n"
        "    expect:\n"
        "      rows: [{game_sk: a, score: 0.0}]\n",
        "select 1 as game_sk, 0.0 as score",
    )
    out = tmp_path / "out"
    schema = _compile(spec, out)
    unit = cast("list[dict[str, Any]]", schema.get("unit_tests") or [])
    assert unit, "unit_tests block missing from schema.yml"
    assert unit[0]["name"] == "score_is_zero_when_rating_is_zero"
    assert unit[0]["model"] == "feat"
