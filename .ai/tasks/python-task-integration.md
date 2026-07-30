# Task — Python-task integration demo

**Status:** ✅ demo shipped; future SQL-transform-tool adapter remains planned.

## Delivered

- Added `experimental/python_tasks/` with dataframe-in/dataframe-out task boundaries.
- Added a pandas task over the existing `core.game` shape:
  numeric imputation, log-scaled rating/count signal, critic score, percentile, and a
  popularity label suitable for an ML training-set example.
- Added a Polars task over nested `rawg__games` genres that produces genre-level counts.
- Added unit tests for feature output, contract drift, and optional Polars execution.
- Documented leakage protection: production labels must come from a future snapshot, not
  the serving/current feature row.

## Acceptance evidence

- Ruff passes for the new task and tests.
- Unit tests pass; the Polars test is skipped when the optional Polars dependency is absent.
- No default `make`, Prefect, SQLMesh, or `spec/` path imports the demo.

## Next step

Add a thin SQL-transform-tool adapter that maps relation inputs to these pure functions and
persists their returned dataframe, without moving the feature logic into orchestration code.
