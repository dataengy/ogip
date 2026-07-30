"""The asset graph `select:` expands against (design §4.3).

Nodes = ODTS assets (spec/sql) + ODOS-declared assets (§4.4, incl. `external: true`).
Edges = authored `depends`, cross-checked against `dialect.table_refs()` — a SQL body
reading a spec asset that `depends` omits is a lineage lie and fails compilation.

Expansion is STATIC (plan-2 decision 3): a selection becomes a concrete topo-ordered
asset list at compile time. `SelectedAsset.exact` carries the §7.3 role: exactly-named
assets project to producer keys, closure members to closure keys.
"""

from __future__ import annotations

import graphlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ogip.spec_compile.bruin import load_assets
from ogip.spec_compile.dialect import table_refs
from ogip.spec_compile.odos.ir import AssetDecl, OdosSpecError, SelectTerm


@dataclass(frozen=True)
class AssetNode:
    name: str
    tags: frozenset[str]


@dataclass(frozen=True)
class SelectedAsset:
    name: str
    exact: bool  # True: named directly (producer key); False: reached via closure


class AssetGraph:
    def __init__(self, nodes: dict[str, AssetNode], edges: set[tuple[str, str]]) -> None:
        unknown = {name for edge in edges for name in edge} - nodes.keys()
        if unknown:
            raise OdosSpecError(f"lineage references unknown assets: {sorted(unknown)}")
        self.nodes = nodes
        self._down: dict[str, set[str]] = {name: set() for name in nodes}
        self._up: dict[str, set[str]] = {name: set() for name in nodes}
        for up, down in edges:
            self._down[up].add(down)
            self._up[down].add(up)
        sorter = graphlib.TopologicalSorter({name: self._up[name] for name in sorted(nodes)})
        try:
            self._topo = list(sorter.static_order())
        except graphlib.CycleError as err:
            raise OdosSpecError(f"asset graph has a cycle: {err.args[1]}") from err

    @classmethod
    def from_spec(cls, spec_sql_dir: Path, declared: Mapping[str, AssetDecl]) -> AssetGraph:
        assets = load_assets(spec_sql_dir)
        nodes: dict[str, AssetNode] = {}
        for asset in assets:
            raw_tags: object = asset.meta.get("tags") or []
            tags: frozenset[str] = (
                frozenset(str(t) for t in cast("list[Any]", raw_tags))
                if isinstance(raw_tags, list)
                else frozenset()
            )
            nodes[asset.name] = AssetNode(asset.name, tags)
        edges: set[tuple[str, str]] = set()
        for asset in assets:
            derived = {r for r in table_refs(asset.sql) if r in nodes and r != asset.name}
            undeclared = sorted(derived - set(asset.depends))
            if undeclared:
                raise OdosSpecError(
                    f"{asset.name}: SQL reads {undeclared} but `depends` does not list "
                    "them — authored lineage and derived lineage disagree"
                )
            for dep in asset.depends:
                edges.add((dep, asset.name))
        for name, decl in declared.items():
            if name in nodes:
                raise OdosSpecError(
                    f"asset {name} is declared in spec/orchestration but already exists in spec/sql"
                )
            nodes[name] = AssetNode(name, frozenset(decl.tags))  # ODOS map-tags -> keys
        return cls(nodes, edges)

    def _closure(self, start: str, step: dict[str, set[str]]) -> set[str]:
        seen, frontier = {start}, [start]
        while frontier:
            for neighbour in step[frontier.pop()]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    frontier.append(neighbour)
        return seen

    def downstream(self, name: str) -> set[str]:
        return self._closure(name, self._down)

    def upstream(self, name: str) -> set[str]:
        return self._closure(name, self._up)

    def expand(self, terms: Sequence[SelectTerm]) -> list[SelectedAsset]:
        picked: dict[str, bool] = {}
        for term in terms:
            if term.kind == "tag":
                hits = [n for n, node in self.nodes.items() if term.name in node.tags]
                if not hits:
                    raise OdosSpecError(f"tag:{term.name} selects nothing")
                for name in hits:
                    picked[name] = True
                continue
            if term.name not in self.nodes:
                raise OdosSpecError(
                    f"select {term.name!r}: unknown asset; known: {sorted(self.nodes)}"
                )
            if term.closure == "exact":
                picked[term.name] = True
            else:
                members = (
                    self.downstream(term.name)
                    if term.closure == "downstream"
                    else self.upstream(term.name)
                )
                for name in members:
                    picked.setdefault(name, False)
        return [SelectedAsset(name, picked[name]) for name in self._topo if name in picked]
