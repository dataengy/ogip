# Task — dbt packages (well-known dbt-hub packages) + jobs that use them

**Status:** 🟡 in progress — 8 core packages install on dbt-duckdb; `dbt deps` wired into builds;
dbt_project_evaluator job added. Extra/opinionated packages + separate tools = follow-ups.

## Packages (emitted into the generated project's `packages.yml` by `to_dbt.py`)

`spec/` is the SSoT, so the dbt project is generated — including `packages.yml`. Version ranges
(not pins) so dbt resolves the newest compatible release.

**Core (default, verified `dbt deps` green on dbt-duckdb):** dbt_utils · codegen · audit_helper ·
dbt_project_evaluator · dbt_external_tables · **godatadriven/dbt_date** (calogica is deprecated) ·
dbt_expectations · dbt_profiler.

**Opt-in (`OGIP_DBT_EXTRA_PACKAGES=1`):** automate_dv (Data Vault — needs DV-shaped models),
elementary (observability — needs its own schema/on-run hooks). Off by default so a plain build
stays fast and unopinionated.

## Wiring

- `jobs/dg-tasks.sh`: `ensure_deps()` runs `dbt deps` once (idempotent — skips if `dbt_packages/`
  present); build/update tasks call it. New `dbt-evaluate` task runs
  `dbt build --select package:dbt_project_evaluator`.
- Dagster: `dbt_project_evaluator_job` + a weekly schedule.

## Not dbt-hub packages (separate tools — evaluated, not wired)

- **dbt-colibri** — a lineage/docs viewer, not a dbt package; runs over the dbt manifest. Fits as
  an optional docs step, not `packages.yml`.
- **chio-labs/sqlbuild** — a standalone SQL build tool; overlaps our spec→engine compiler. Belongs
  in `docs/comparisons/` (plain-sql-vs-frameworks) rather than the production path.

## Follow-ups

- Demonstrate a package in a model/test via `spec/` (e.g. a `dbt_expectations` check) — needs a
  spec change (SSoT), so it goes through the spec/core-pipeline lane.
- elementary/automate_dv real runs need schema setup / DV models.
