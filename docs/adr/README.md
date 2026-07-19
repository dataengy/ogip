# Architecture Decision Records (ADRs)

Point-in-time architecture decisions for OGIP. One decision per file, immutable once
`Accepted` — superseded decisions get a new ADR that references the old one. Format:
lightweight [MADR](https://adr.github.io/madr/)/Nygard (Status · Context · Decision ·
Consequences · Alternatives). Use [`_template.md`](_template.md) for new records.

These ADRs formalize the locked decisions in [`.ai/PLAN.md`](../../.ai/PLAN.md) Part C (D0–D13).

| ADR | Title | Decision | Status |
|---|---|---|---|
| [0001](ADR-0001-edw-layering-no-medallion.md) | Classical EDW layering, no medallion | raw0 · stg · core · star · am · marts · fs | Accepted |
| [0002](ADR-0002-duckdb-analytical-engine.md) | DuckDB as the analytical engine | in-process OLAP, runs in CI | Accepted |
| [0003](ADR-0003-parquet-lake-defer-iceberg-ducklake.md) | Parquet lake; defer Iceberg/DuckLake | Parquet on FS/R2; table formats = research | Accepted |
| [0004](ADR-0004-sqlmesh-default-transform-engine.md) | SQLMesh as the default transform engine | D5 | Accepted |
| [0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) | `spec/` SSoT: Bruin + ODCS + compiler | D0/D5 | Accepted |
| [0006](ADR-0006-dlt-default-ingestion-postgres-landing.md) | dlt default ingestion + Postgres landing; ingestr CDC | D11 | Accepted |
| [0007](ADR-0007-prefect-orchestration.md) | Prefect 3 orchestration + runnable alt setups | D1/D3 | Accepted |
| [0008](ADR-0008-postgresql-roles.md) | PostgreSQL roles: landing + platform_meta + Prefect | D9 | Accepted |
| [0009](ADR-0009-ml-outputs-feature-store.md) | Product = ML outputs + Feature Store; no BI/semantic in core | D6/D7/D8 | Accepted |
| [0010](ADR-0010-activity-model-layer.md) | Activity Model (Activity Schema) layer | D13 | Accepted |
| [0011](ADR-0011-minimal-secrets.md) | Minimal secrets: `.env` + GitHub Actions secrets | D10 | Accepted |
| [0012](ADR-0012-github-ci-manual-vps-deploy.md) | GitHub Actions CI + manual VPS deploy (DevOps separate) | D9 | Accepted |
| [0013](ADR-0013-github-issues-projects-tasks.md) | GitHub Issues/Projects as the task tracker | D12 | Accepted |
| [0014](ADR-0014-resilient-scraping-concurrency.md) | Resilient scraping: async-first, effectively-once landing | A6/D11 scraper pattern | Proposed |
| [0015](ADR-0015-dagster-alt-orchestration-dg-components.md) | Dagster alt-orchestration via `dg` Components (dbt + dlt + ingestr CDC) | ADR-0007 alt setup, D1/D11 | Accepted |
| [0016](ADR-0016-orchestrator-transform-dq-boundary.md) | Orchestrator/transform responsibility boundary (no DQ duplication in Dagster) | DQ lives in spec→dbt/SQLMesh; orchestrator only surfaces | Accepted |

New ADRs are numbered sequentially (`ADR-NNNN-kebab-title.md`) and added to this table.
