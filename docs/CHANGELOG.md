# Changelog

All notable changes to OGIP are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Dagster alt-orchestration (dbt + dlt + ingestr CDC)
- `experimental/orchestration/dagster_ogip/` — self-contained `dg` CLI + Components project
  ([ADR-0015](adr/ADR-0015-dagster-alt-orchestration-dg-components.md)): `DbtProjectComponent`
  (`select: tag:daily`, dbt project generated from `spec/` via `to_dbt.py`), native
  `DltLoadCollectionComponent` (RAWG → raw Parquet), and an ingestr **CDC** asset (D11).
- dev/prod instances (SQLite vs Postgres, env-refs only).
- **Combo e2e** `e2e/run_combo.sh` — drives source → FS layer through Dagster (dlt → dbt build +
  tests → assert `fs.market_features`); a separate `dagster-e2e` GitHub workflow runs it.
- Runbook [docs/runbooks/run-dagster.md](runbooks/run-dagster.md).

### Added — M0 walking skeleton
- End-to-end vertical slice: **RAWG → raw Parquet (dlt) → SQLMesh (raw→stg→core→fs, compiled from
  Bruin spec) → ML-ready `games.parquet` + `market_features.parquet` → demo notebook**, on a Prefect flow.
- `ingestion/` (BaseSource family + dlt), `spec/` (ODCS contract + Bruin SQL), `src/ogip/spec_compile`
  (Bruin→SQLMesh), `src/ogip/warehouse` (Parquet export), `pipelines/flows/main.py` (Prefect).
- e2e test runs the Prefect job and asserts outputs; CI gains an `e2e` job (runs the pipeline). CI green 7/7.
- Shipped to [dataengy/ogip](https://github.com/dataengy/ogip).

### Added — Phase 0 scaffold
- Project inception at `~/gi/@dataengy/OGIP` (successor to OGAP).
- Master creation plan (`.ai/PLAN.md`): target design + 11-phase build + locked decisions D0–D12.
- Production stack locked: Prefect 3 + **dlt** (default ingestion) + **SQLMesh** (default engine,
  from spec) + DuckDB + Parquet/PyArrow on **Cloudflare R2** + **PostgreSQL** (landing zone +
  platform_meta + Prefect backend); manual VPS deploy (DevOps separate).
- Two-stage ingestion: scraped/parsed data → Postgres `landing` → dlt (default) / **ingestr CDC** (optional).
- Complete alternative setups: **Prefect+Bruin** and **Prefect+Dagster-over-dlt/dbt** (runnable profiles).
- Layers (no medallion): `0 raw <system>__<table>` → `stg` → `core` → `star` → **`am` (Activity
  Schema)** → `marts` → **`fs` (feature store)**; JupyterLab demo notebooks; optional Evidence
  visualizer; **spec** = Bruin format + ODCS, SSoT.
- Secrets: minimal & lightest — gitignored `.env` + GitHub Actions secrets (Bitwarden/git-secret opt-in).
- Task tracking: `.ai/TODO.md` + `.ai/tasks/` synced to **GitHub Issues/Projects** (`just tasks-sync`).
- **Delivery strategy** = walking-skeleton MVP first, then replicate across toolsets; run in
  Docker + Prefect after each (`integrations/prefect/`).
- Docs scaffolding: `docs/adr/` (index + template + 13 ADRs), `docs/architecture/`
  (README + overview), `docs/runbooks/` (README + template + 4 runbooks).
- `.ai/` agentic hub (AGENTS · CLAUDE · README · STATUS · PLAN · TODO · tasks/), `docs/` stubs,
  `.run/` (runtime) + `.tmp/` (temp scripts) conventions.

_Build begins at Phase 0 (Scaffold & identity) after plan approval._
