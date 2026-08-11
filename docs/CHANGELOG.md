# Changelog

All notable changes to OGIP are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Opt-in secrets sync + new-workstation runbook (2026-08-11)
- ADR-0011's opt-in backends are now implemented (#52): `config/.env-secrets-render.sh`
  (`pull`/`push` for Bitwarden CLI, `hide`/`reveal`/`setup-git-secret` for git-secret,
  `doctor` readiness report), `just secrets-*` recipes with dry siblings; slot names stay
  sourced from `config/.env-render.py → SECRET_SLOTS`, values are never printed.
- Fixed the inverted `.gitignore` rule that ignored the committed `config/secrets/*.secret`
  blobs; plaintext under `config/secrets/` is now the only thing ignored.
- `docs/comparisons/secrets-management.md` (adoption analysis) and
  `docs/runbooks/new-workstation.md` (settled old machine → bootstrapped new machine);
  dbt deps lockfile committed on `lane/dagster` for reproducible package resolution.

### Added — DQ monitor executor + dbt/Bruin primary landing (2026-07-30)
- `dq/run.py` executes the declared monitors (row_count + freshness) against the DuckDB
  warehouse: `error` severity blocks with exit 1 (ADR-0008); in `make check` (loud SKIP on a
  fresh checkout) and in the CI e2e step. Caught a real gap on day one: `core.console_pricing`
  was empty on demo data — the PSN sample now matches a game in the RAWG demo set (Portal 2).
- Re-root merged (PR #46): dbt primary + Bruin co-primary (ADR-0020), `prefect-dbt` default,
  three demo commands green (`run-dbt` · `run-bruin` · `run-dagster-dbt`), Bruin CLI in CI,
  `kind:"dbt"` selection fixes the standing combo-e2e failure, T9 landing scripts
  (`just preflight` · `just gh-merge-as`).
- Local/CI lint parity (#39): the nested dagster project is linted explicitly on both sides.
- Loud TBD stubs for `integrations/prefect/{deploy,trigger}.py` (#11/#17); layer READMEs for
  `spec/sql*` + `spec/contracts` (closes F4); ODTS 0.2 proposals committed behind their
  pre-normative banner.

### Changed — Finalization run started (2026-07-30)
- Plan of record: `docs/superpowers/plans/2026-07-30-finalization-land-everything.md`
  (umbrella `.ai/tasks/finalization.md`): three green run commands (`run-dbt` · `run-bruin` ·
  `run-dagster-dbt`) → re-root T4–T9 (#40) → land dagster #34 + odos #37 → dev→main (#10).
- Ground cleared: `lane/odos-compiler` safety-pushed; 3 stale session locks broken; corrupted
  `pipelines/dbt/prefect.yaml` restored (name/prefect-version keys); local `dev` reconciled.
- Frozen-feature register added: `docs/techdebt/finalization-tbd.md` (8 entries, loud-stub rule).

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
