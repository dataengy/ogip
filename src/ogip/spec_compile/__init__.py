"""Spec compiler (ADR-0005): render engine-agnostic `spec/sql` (Bruin asset format) into
engine-native projects. The default engine is **SQLMesh**; dbt, SQLMesh-over-dbt and Bruin
are the comparison setups (A12). Thin by design — the only place engine specifics live
above ``spec/sql/_ext/``.
"""

from .bruin import Asset, asset_paths, load_assets, parse_asset
from .dialect import SPEC_DIALECT, SqlSpecError, table_refs, transpile
from .to_bruin import compile_to_bruin
from .to_dbt import compile_to_dbt
from .to_sqlmesh import compile_to_sqlmesh
from .to_sqlmesh_dbt import compile_to_sqlmesh_over_dbt

__all__ = [
    "SPEC_DIALECT",
    "Asset",
    "SqlSpecError",
    "asset_paths",
    "compile_to_bruin",
    "compile_to_dbt",
    "compile_to_sqlmesh",
    "compile_to_sqlmesh_over_dbt",
    "load_assets",
    "parse_asset",
    "table_refs",
    "transpile",
]
