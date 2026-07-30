# OGIP — TODO

Short, ordered, near-term actions. Each references a detailed task file in [tasks/](tasks/)
and/or a phase in [PLAN.md](PLAN.md) · [../docs/ROADMAP.md](../docs/ROADMAP.md). Delivery is
**walking-skeleton first** (D14): thin vertical slice end-to-end, then replicate across toolsets.
Sync to GitHub Issues/Projects with `just tasks-sync`. Keep this list short.

- [x] **Go / no-go** — approved; spec compiler kept (thin Bruin→SQLMesh shim in M0).
- [x] **Phase 0 — Scaffold & identity** — shipped, CI green → `tasks/phase-0-scaffold.md`
- [x] **M0 — walking skeleton** (RAWG → dlt raw → SQLMesh → ML parquet → notebook, Prefect;
      e2e in CI) — shipped, CI 7/7 → `tasks/m0-walking-skeleton.md` _(Evidence + Docker `make up` deferred to M1)_
- [ ] **P1 · Resilient scraping slice** — async `ScraperSource`
      ([ADR-0014](../docs/adr/ADR-0014-resilient-scraping-concurrency.md)) + Postgres landing +
      HLTB end to end → `tasks/scraping-resilient.md` _(lane `ingestion`)_
- [ ] **P1 · Finalize R2 + VPS deploy** — staged s3 call sites + spec-compiler lake root +
      `integrations/prefect/deploy.py` + real R2 bucket + host deploy/smoke
      → `tasks/r2-vps-finalize.md` _(lane `core-pipeline`; umbrella over the remainder of
      `tasks/{s3-object-storage,vps-deploy-tooling}.md`)_
- [ ] **P2 · Sources backlog** — candidates mapped to games-market models (pricing · scope ·
      budget · traction · quality) → `tasks/sources-backlog.md`
- [x] **P2 · Python-task integration demo** — pandas/Polars ML feature tasks over RAWG/core
      data, with adapter-shaped dataframe boundaries → `tasks/python-task-integration.md`
- [ ] **`spec/` semantic layer (Bruin Semantic Layer)** — engine-agnostic semantic
      description in `spec/` _(mid-prio)_ → `tasks/spec-semantic-layer.md`
- [ ] **M1–M4 — replicate the slice** across `prefect-bruin` · `prefect-dbt` ·
      `prefect-sqlmesh-over-dbt` · `prefect-dagster-dlt-dbt`; add Evidence visualizer
      _(demoted below the P1s)_ → `tasks/m1-m4-toolsets.md`
- [ ] **Broaden (Phases 4–10)**: DQ, star/am/fs depth, observability wiring, README polish
      → `tasks/phase-*.md`

Open requirement questions (scraping · volumes · serving/FS/semantic · SQL+Python):
[../docs/OPEN-QUESTIONS.md](../docs/OPEN-QUESTIONS.md).

_Detail per phase lives in `tasks/`; this is the driver checklist._
