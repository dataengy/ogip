# `transform/`

The production transform: **SQLMesh** (ADR-0004, D5), compiled from `spec/` and run on DuckDB,
sequenced by Prefect. Builds `staging → core → star / am → marts → fs`.

- `sqlmesh/` — the generated SQLMesh project (from `src/ogip/spec_compile/`).
- `runner.py` — plain-SQL runner (comparison profile `prefect-sql`).

_Built from Phase 3; M0 wires the minimal RAWG slice._
