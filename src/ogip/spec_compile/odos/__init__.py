"""ODOS compiler frontend (design §8) — IR, asset graph, loader. Adapters live beside
`spec_compile` as `to_dagster.py` / `to_prefect.py`; they consume `load_spec()`'s output."""

from ogip.spec_compile.odos.frontend import OdosSpec, ResolvedJob, load_spec
from ogip.spec_compile.odos.ir import ODOS_VERSION, OdosSpecError

__all__ = [
    "ODOS_VERSION",
    "OdosSpec",
    "OdosSpecError",
    "ResolvedJob",
    "load_spec",
]
