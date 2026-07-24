# OGIP — Roadmap

Phased delivery with a **user approval gate after each phase**. Full detail and acceptance
criteria live in [.ai/PLAN.md](../.ai/PLAN.md); this is the at-a-glance map. Requirement
unknowns that steer this map live in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md).

## Current priorities (reprioritized 2026-07-17)

| # | Item | Lane | Detail |
|---|---|---|---|
| **P1** | **Resilient scraping slice** — async `ScraperSource` ([ADR-0014](adr/ADR-0014-resilient-scraping-concurrency.md)) + Postgres landing + first scraped source (HLTB) end to end | `ingestion` | [.ai/tasks/scraping-resilient.md](../.ai/tasks/scraping-resilient.md) |
| **P1** | **Finalize R2 + VPS deploy** — close the staged s3/vps handoffs: storage-seam call sites, spec-compiler lake root, `integrations/prefect/deploy.py`, real R2 bucket, host deploy + smoke | `core-pipeline` | [.ai/tasks/r2-vps-finalize.md](../.ai/tasks/r2-vps-finalize.md) |
| P2 | **Sources backlog** — candidates mapped to games-market models (pricing · scope · budget · traction · quality) | backlog | [.ai/tasks/sources-backlog.md](../.ai/tasks/sources-backlog.md) |
| P2 | **Python-task integration demo** — pandas/Polars ML preparation tasks over RAWG/core data, ready for a future SQL-transform-tool adapter | experimental | [.ai/tasks/python-task-integration.md](../.ai/tasks/python-task-integration.md) |
| mid | `spec/` semantic layer (engine-agnostic, Bruin format) | `spec` | [.ai/tasks/spec-semantic-layer.md](../.ai/tasks/spec-semantic-layer.md) |
| then | M1–M4 — replicate the M0 slice across alt toolsets (bruin · dbt · sqlmesh-over-dbt · dagster) — *demoted below the P1s* | `core-pipeline` / `dagster` | [.ai/PLAN.md](../.ai/PLAN.md) |

## Phase map

| Phase | Deliverable | Status |
|---|---|---|
| 0 | **Scaffold & identity** — git init, pyproject (uv), tooling, config SSoT, secrets, CI, task-sync + TODO | ✅ shipped |
| M0 | **Walking skeleton** — RAWG → dlt raw → SQLMesh (from spec) → ML parquet + notebook, on Prefect; e2e in CI | ✅ shipped (CI 7/7) |
| 1 | **`spec/` SSoT** — ODCS contracts + Bruin-format portable SQL (incl. `fs/`) + DQ + lineage | 🟡 M0 slice only |
| 2 | **Ingestion (dlt) + Steam/RAWG** — `BaseSource`→dlt; Postgres `landing` + **scraping ([ADR-0014](adr/ADR-0014-resilient-scraping-concurrency.md))** | 🟡 RAWG shipped; **scraping = P1** |
| 3 | **Transform (SQLMesh default)** — spec compiler + SQLMesh on DuckDB, `staging→core→{star,am}→marts→fs` | 🟡 M0 slice (raw→stg→core→fs) |
| 4 | **Data quality** — freshness · uniqueness · RI · business rules | ⬜ planned |
| 5 | **ML-ready outputs + notebooks** — 6 `*.parquet` (marts + FS); DATASETS.md; JupyterLab demos | 🟡 2 outputs + 1 notebook (M0) |
| 6 | **Orchestration (Prefect) + Postgres** — end-to-end `make run`; `platform_meta`; ephemeral + server profiles | 🟡 ephemeral flow shipped; server profile + `platform_meta` pending |
| 7 | **Observability** — VictoriaMetrics + Loki + Alloy + Grafana; alerts abstraction | 🟡 stack + `Notifier` shipped; pipeline instrumentation pending |
| 8 | **Remaining sources + cloud storage** — Steam Reviews, IGDB, Reddit, Twitch, HLTB, Metacritic; R2/MinIO/S3 profiles | 🟡 storage seam + MinIO shipped; **R2 finalize = P1**; sources → [backlog](../.ai/tasks/sources-backlog.md) |
| 9 | **Comparisons + runnable profiles + research** — spec compiler → dbt/Bruin; engine/orchestration profiles; feature-store-tools + Evidence analyses | ⬜ planned |
| 10 | **VPS deploy + README + polish** — manual VPS runbook (DevOps separate); outcome-first README; final audit | 🟡 `deploy/vps/` tooling shipped; **real host deploy = P1** |

**Fast slice (D4):** Phases 0–6 on **Steam + RAWG** give a working end-to-end
`sources → raw → SQL → ML parquet` demo; observability, the rest of the sources, and the
experimental profiles layer on afterward.
