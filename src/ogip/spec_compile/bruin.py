"""Parse Bruin-format SQL assets: a ``/* @bruin <yaml> @bruin */`` header + a SQL body."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

_BRUIN = re.compile(r"/\*\s*@bruin\s*(?P<yaml>.*?)\s*@bruin\s*\*/\s*(?P<sql>.*)", re.DOTALL)


@dataclass(frozen=True)
class Asset:
    """A parsed Bruin asset — SQL + inline metadata (lineage, DQ, ownership)."""

    name: str  # "<schema>.<model>"
    materialization: str  # "table" | "view"
    sql: str
    depends: list[str]
    meta: dict[str, Any]

    @property
    def schema(self) -> str:
        return self.name.split(".", 1)[0]

    @property
    def model(self) -> str:
        return self.name.split(".", 1)[1]


def parse_asset(path: Path) -> Asset:
    match = _BRUIN.match(path.read_text(encoding="utf-8").strip())
    if match is None:
        raise ValueError(f"{path}: not a Bruin asset (missing @bruin header)")
    loaded = yaml.safe_load(match.group("yaml"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: @bruin header is not a YAML mapping")
    meta = cast("dict[str, Any]", loaded)

    materialization = meta.get("materialization")
    mtype = "table"
    if isinstance(materialization, dict):
        mtype = str(cast("dict[str, Any]", materialization).get("type", "table"))

    depends_value = meta.get("depends")
    depends = (
        [str(d) for d in cast("list[Any]", depends_value)]
        if isinstance(depends_value, list)
        else []
    )
    return Asset(
        name=str(meta["name"]),
        materialization=mtype,
        sql=match.group("sql").strip(),
        depends=depends,
        meta=meta,
    )


def load_assets(spec_sql_dir: Path) -> list[Asset]:
    """Parse every `spec/sql/**/*.sql` (skipping engine-specific `_ext/` overrides)."""
    return [parse_asset(p) for p in sorted(spec_sql_dir.rglob("*.sql")) if "_ext" not in p.parts]
