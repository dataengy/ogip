"""Spec compiler (ADR-0005): render engine-agnostic `spec/sql` (Bruin asset format) into
engine-native projects. M0 target: **SQLMesh** (default engine). Thin by design — the only
place engine specifics live above ``spec/sql/_ext/``.
"""

from .bruin import Asset, load_assets, parse_asset
from .to_sqlmesh import compile_to_sqlmesh

__all__ = ["Asset", "compile_to_sqlmesh", "load_assets", "parse_asset"]
