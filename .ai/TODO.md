# OGIP — TODO

Short, ordered, near-term actions. Each references a detailed task file in [tasks/](tasks/)
and/or a phase in [PLAN.md](PLAN.md) · [../docs/ROADMAP.md](../docs/ROADMAP.md). Delivery is
**walking-skeleton first** (D14): thin vertical slice end-to-end, then replicate across toolsets.
Sync to GitHub Issues/Projects with `just tasks-sync`. Keep this list short.

- [ ] **Go / no-go** on the finalized plan ([PLAN.md](PLAN.md), D0–D14); confirm spec-compiler
      approach (keep as thin shim in M0, vs author-native SQLMesh) → `tasks/decisions.md`
- [ ] **Phase 0 — Scaffold & identity**: git init, pyproject/uv, tooling, config SSoT, secrets,
      CI, task-sync, `.run/`/`.tmp/` → `tasks/phase-0-scaffold.md`
- [ ] **M0 — walking skeleton** (RAWG → raw → spec → SQLMesh → ML parquet → notebook + Evidence,
      on Prefect+dlt); then `make up` (Docker) + Prefect job green → `tasks/m0-walking-skeleton.md`
- [ ] **M1–M4 — replicate the slice** across `prefect-bruin` · `prefect-dbt` ·
      `prefect-sqlmesh-over-dbt` · `prefect-dagster-dlt-dbt` → `tasks/m1-m4-toolsets.md`
- [ ] **Broaden (Phases 4–10)**: DQ, star/am/fs depth, more sources, observability, VPS deploy,
      README polish → `tasks/phase-*.md`

_Detail per phase lives in `tasks/`; this is the driver checklist._
