"""Unit tests for the spec compiler's engine generators + the plain-SQL runner.

These pin the A12 contract: every transform setup is *derived* from `spec/sql` (Bruin
format) — Bruin gets a verbatim pass-through, dbt/SQLMesh-over-dbt get generated projects,
and the plain-SQL runner executes the spec directly in `depends` order.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import duckdb
import pytest
import yaml
from transform.runner import execution_order, run_plain_sql

from ogip.spec_compile import (
    SqlSpecError,
    compile_to_bruin,
    compile_to_sqlmesh_over_dbt,
    load_assets,
    table_refs,
    transpile,
)
from ogip.spec_compile.__main__ import main as spec_compile_main
from ogip.spec_compile.dialect import rewrite_refs

REPO = Path(__file__).resolve().parents[3]
SPEC_SQL = REPO / "spec" / "sql"

# Alphabetical load order (aa before zz) is the WRONG execution order here — only the
# declared `depends` lineage can sequence these correctly.
_BASE = """/* @bruin
name: zz.base
type: duckdb.sql
materialization:
  type: view
@bruin */
select 1 as id
"""
_FINAL = """/* @bruin
name: aa.final
type: duckdb.sql
materialization:
  type: table
depends:
  - zz.base
  - warehouse.external_thing
@bruin */
select id * 10 as id10 from zz.base
"""


@pytest.fixture
def tiny_spec(tmp_path: Path) -> Path:
    spec = tmp_path / "sql"
    (spec / "aa").mkdir(parents=True)
    (spec / "zz").mkdir(parents=True)
    (spec / "aa" / "final.sql").write_text(_FINAL, encoding="utf-8")
    (spec / "zz" / "base.sql").write_text(_BASE, encoding="utf-8")
    return spec


def test_execution_order_follows_depends_not_names(tiny_spec: Path) -> None:
    ordered = [a.name for a in execution_order(load_assets(tiny_spec))]
    assert ordered == ["zz.base", "aa.final"]  # external dep is inert, lineage wins


def test_runner_builds_relations_with_declared_materializations(
    tiny_spec: Path, tmp_path: Path
) -> None:
    warehouse = tmp_path / "wh.duckdb"
    built = run_plain_sql(tiny_spec, warehouse)
    assert built == ["zz.base", "aa.final"]

    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        assert con.execute("select id10 from aa.final").fetchall() == [(10,)]
        types = dict(
            con.execute("select table_schema, table_type from information_schema.tables").fetchall()
        )
        assert types["zz"] == "VIEW"
        assert types["aa"] == "BASE TABLE"
    finally:
        con.close()


def test_to_bruin_is_verbatim_passthrough_plus_shell(tmp_path: Path) -> None:
    project = tmp_path / "bruin"
    warehouse = Path(".run/data/warehouse/ogip.duckdb")
    names = compile_to_bruin(SPEC_SQL, project, warehouse=warehouse)
    assert "raw.rawg__games" in names

    copied = (project / "assets" / "raw" / "rawg__games.sql").read_text(encoding="utf-8")
    original = (SPEC_SQL / "raw" / "rawg__games.sql").read_text(encoding="utf-8")
    assert copied == original  # spec IS Bruin — the asset must survive untouched

    env = yaml.safe_load((project / ".bruin.yml").read_text(encoding="utf-8"))
    connection = env["environments"]["default"]["connections"]["duckdb"][0]
    assert connection["path"] == str(warehouse)
    pipeline = yaml.safe_load((project / "pipeline.yml").read_text(encoding="utf-8"))
    assert pipeline["default_connections"]["duckdb"] == connection["name"]


def test_to_sqlmesh_over_dbt_emits_dbt_project_plus_loader_config(tmp_path: Path) -> None:
    project = tmp_path / "sqlmesh_dbt"
    names = compile_to_sqlmesh_over_dbt(
        SPEC_SQL, project, warehouse=Path(".run/data/warehouse/ogip.duckdb"), repo_root=Path()
    )
    assert "fs.market_features" in names
    assert (project / "dbt_project.yml").is_file()
    assert "sqlmesh_config" in (project / "config.py").read_text(encoding="utf-8")
    # committed output must stay machine-independent: no absolute runtime paths
    model = (project / "models" / "raw" / "rawg__games.sql").read_text(encoding="utf-8")
    assert "'./.run/" in model


def test_cli_generates_every_engine_project(tmp_path: Path) -> None:
    assert spec_compile_main(["all", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "sqlmesh" / "models" / "core" / "game.sql").is_file()
    assert (tmp_path / "dbt" / "dbt_project.yml").is_file()
    assert (tmp_path / "sqlmesh_dbt" / "config.py").is_file()
    assert (tmp_path / "bruin" / "pipeline.yml").is_file()


def test_ref_rewriting_ignores_matches_inside_string_literals() -> None:
    """The regression the AST rewrite exists for — text substitution corrupts this SQL."""
    sql = "select n from core.game where note = 'core.game was renamed'"
    out = rewrite_refs(sql, {"core.game": "{{ ref('game') }}"})
    assert "FROM {{ ref('game') }}" in out
    assert "'core.game was renamed'" in out  # literal untouched


def test_derived_lineage_matches_declared_depends() -> None:
    """`depends` is hand-written; the SQL is the truth. Disagreement means one is wrong."""
    assets = load_assets(SPEC_SQL)
    names = {a.name for a in assets}
    for asset in assets:
        derived = {ref for ref in table_refs(asset.sql) if ref in names}
        assert derived <= set(asset.depends), (
            f"{asset.name}: reads {derived - set(asset.depends)} but does not declare it"
        )


@pytest.mark.parametrize("target", ["postgres", "clickhouse", "bigquery"])
def test_spec_sql_survives_retargeting(target: str) -> None:
    """The portable-SQL policy (ADR-0016), executable: every model retargets cleanly."""
    for asset in load_assets(SPEC_SQL):
        assert transpile(asset.sql, write=target)


def test_unparseable_spec_sql_fails_at_compile_time() -> None:
    with pytest.raises(SqlSpecError):
        table_refs("select from where )(")


def _load_run_profile() -> ModuleType:
    path = REPO / "src" / "scripts" / "run-profile.py"
    spec = importlib.util.spec_from_file_location("run_profile", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_profiles_resolve_from_config_ssot() -> None:
    run_profile = _load_run_profile()
    profiles = run_profile.load_profiles()

    default_name, default = run_profile.resolve_profile(profiles, None)
    assert default_name == "prefect-sqlmesh"
    assert default["transform"] == "sqlmesh"

    _, plain = run_profile.resolve_profile(profiles, "prefect-sql")
    assert plain["transform"] == "plain_sql"

    with pytest.raises(SystemExit):
        run_profile.resolve_profile(profiles, "no-such-profile")
