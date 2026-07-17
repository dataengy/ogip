# OGIP — Roadmap

Phased delivery with a **user approval gate after each phase**. Full detail and acceptance
criteria live in [.ai/PLAN.md](../.ai/PLAN.md); this is the at-a-glance map.

| Phase | Deliverable | Status |
|---|---|---|
| 0 | **Scaffold & identity** — git init, pyproject (uv), tooling, config SSoT, secrets, CI, task-sync + TODO | ⬜ planned |
| 1 | **`spec/` SSoT** — ODCS contracts + Bruin-format portable SQL (incl. `fs/`) + DQ + lineage | ⬜ planned |
| 2 | **Ingestion (dlt) + Steam/RAWG** — `BaseSource`→dlt; Postgres `landing` for scraped/parsed → raw Parquet | ⬜ planned |
| 3 | **Transform (SQLMesh default)** — spec compiler + SQLMesh on DuckDB, `staging→core→{star,am}→marts→fs` | ⬜ planned |
| 4 | **Data quality** — freshness · uniqueness · RI · business rules | ⬜ planned |
| 5 | **ML-ready outputs + notebooks** — 6 `*.parquet` (marts + FS); DATASETS.md; JupyterLab demos | ⬜ planned |
| 6 | **Orchestration (Prefect) + Postgres** — end-to-end `make run`; `platform_meta`; ephemeral + server profiles | ⬜ planned |
| 7 | **Observability** — VictoriaMetrics + Loki + Alloy + Grafana; alerts abstraction | ⬜ planned |
| 8 | **Remaining sources + cloud storage** — Steam Reviews, IGDB, Reddit, Twitch, HLTB, Metacritic; R2/MinIO/S3 profiles | ⬜ planned |
| 9 | **Comparisons + runnable profiles + research** — spec compiler → dbt/Bruin; engine/orchestration profiles; feature-store-tools + Evidence analyses | ⬜ planned |
| 10 | **VPS deploy + README + polish** — manual VPS runbook (DevOps separate); outcome-first README; final audit | ⬜ planned |

**Fast slice (D4):** Phases 0–6 on **Steam + RAWG** give a working end-to-end
`sources → raw → SQL → ML parquet` demo; observability, the rest of the sources, and the
experimental profiles layer on afterward.
