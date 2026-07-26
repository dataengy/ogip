"""ODOS compiler frontend (design §8) — IR, asset graph, loader. Adapters live beside
`spec_compile` as `to_dagster.py` / `to_prefect.py`; they consume `load_spec()`'s output."""

# frontend/graph re-exports land in Task 7
from ogip.spec_compile.odos.ir import ODOS_VERSION, OdosSpecError

__all__ = ["ODOS_VERSION", "OdosSpecError"]
