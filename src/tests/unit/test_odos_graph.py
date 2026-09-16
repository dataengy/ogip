"""Select expansion against ODTS lineage — closures, tags, and the lineage-lie guard."""

from pathlib import Path

import pytest

from ogip.spec_compile.odos.graph import AssetGraph
from ogip.spec_compile.odos.ir import AssetDecl, OdosSpecError, parse_select

_SPEC_SQL = Path(__file__).resolve().parents[3] / "spec" / "sql"


def _write(spec: Path, rel: str, name: str, depends: list[str], sql: str) -> None:
    dep_block = "".join(f"  - {d}\n" for d in depends)
    header = f"name: {name}\ntags: [t_{name.split('.')[0]}]\n"
    if depends:
        header += f"depends:\n{dep_block}"
    target = spec / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"/* @bruin\n{header}@bruin */\n{sql}\n")


@pytest.fixture()
def toy_spec(tmp_path: Path) -> Path:
    _write(tmp_path, "raw/a.sql", "raw.a", [], "select 1 as x")
    _write(tmp_path, "staging/b.sql", "staging.b", ["raw.a"], "select x from raw.a")
    _write(tmp_path, "core/c.sql", "core.c", ["staging.b"], "select x from staging.b")
    return tmp_path


def test_real_spec_builds_and_has_the_four_layers() -> None:
    graph = AssetGraph.from_spec(_SPEC_SQL, {})
    for name in ("raw.rawg__games", "staging.stg_games", "core.game", "fs.market_features"):
        assert name in graph.nodes


def test_downstream_closure_is_topo_ordered_and_marks_roles(toy_spec: Path) -> None:
    graph = AssetGraph.from_spec(toy_spec, {})
    expanded = graph.expand(parse_select("raw.a+"))
    assert [(s.name, s.exact) for s in expanded] == [
        ("raw.a", False),
        ("staging.b", False),
        ("core.c", False),
    ]


def test_exact_select_marks_exact(toy_spec: Path) -> None:
    graph = AssetGraph.from_spec(toy_spec, {})
    assert [(s.name, s.exact) for s in graph.expand(parse_select("staging.b"))] == [
        ("staging.b", True)
    ]


def test_upstream_closure(toy_spec: Path) -> None:
    graph = AssetGraph.from_spec(toy_spec, {})
    assert [s.name for s in graph.expand(parse_select("+core.c"))] == [
        "raw.a",
        "staging.b",
        "core.c",
    ]


def test_tag_selection_and_empty_tag_error(toy_spec: Path) -> None:
    graph = AssetGraph.from_spec(toy_spec, {})
    assert [s.name for s in graph.expand(parse_select("tag:t_raw"))] == ["raw.a"]
    with pytest.raises(OdosSpecError, match="selects nothing"):
        graph.expand(parse_select("tag:nope"))


def test_unknown_asset_is_a_compile_error(toy_spec: Path) -> None:
    graph = AssetGraph.from_spec(toy_spec, {})
    with pytest.raises(OdosSpecError, match="unknown asset"):
        graph.expand(parse_select("raw.missing"))


def test_declared_assets_join_the_graph(toy_spec: Path) -> None:
    declared = {"fs.snap": AssetDecl.model_validate({"task": "snapshot.write"})}
    graph = AssetGraph.from_spec(toy_spec, declared)
    assert [s.name for s in graph.expand(parse_select("fs.snap"))] == ["fs.snap"]


def test_sql_ref_missing_from_depends_is_a_lineage_lie(toy_spec: Path) -> None:
    """§4.3 derives the graph from depends + table_refs; the two disagreeing = one is wrong."""
    _write(toy_spec, "fs/d.sql", "fs.d", [], "select x from core.c")
    with pytest.raises(OdosSpecError, match="depends"):
        AssetGraph.from_spec(toy_spec, {})
