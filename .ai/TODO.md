# OGIP — TODO

Short, ordered, near-term actions. Each references a detailed task file in [tasks/](tasks/)
and/or a phase in [PLAN.md](PLAN.md) · [../docs/ROADMAP.md](../docs/ROADMAP.md). Delivery is
**walking-skeleton first** (D14): thin vertical slice end-to-end, then replicate across toolsets.
Sync to GitHub Issues/Projects with `just tasks-sync`. Keep this list short.

- [x] **Go / no-go** — approved; spec compiler kept (thin Bruin→SQLMesh shim in M0).
- [x] **Phase 0 — Scaffold & identity** — shipped, CI green → `tasks/phase-0-scaffold.md`
- [x] **M0 — walking skeleton** (RAWG → dlt raw → SQLMesh → ML parquet → notebook, Prefect;
      e2e in CI) — shipped, CI 7/7 → `tasks/m0-walking-skeleton.md` _(Evidence + Docker `make up` deferred to M1)_
- [ ] **M1–M4 — replicate the slice** across `prefect-bruin` · `prefect-dbt` ·
      `prefect-sqlmesh-over-dbt` · `prefect-dagster-dlt-dbt`; add Evidence visualizer → `tasks/m1-m4-toolsets.md`
- [ ] **Broaden (Phases 4–10)**: DQ, star/am/fs depth, more sources, observability, VPS deploy,
      README polish → `tasks/phase-*.md`

_Detail per phase lives in `tasks/`; this is the driver checklist._
