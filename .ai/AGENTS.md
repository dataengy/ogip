# AGENTS.md — instructions for AI agents working in OGIP

**OGIP (Open Games Intelligence Platform)** — a portfolio-grade **Market Intelligence
Platform**: it collects public gaming-market data, transforms it with plain SQL on DuckDB,
and ships **ML-ready Parquet datasets** for Data Scientists, ML Engineers, and Analysts
(**not** BI users). Read [docs/architecture/overview.md](../docs/architecture/overview.md) before
structural changes; record decisions as [ADRs in docs/adr/](../docs/adr/); the master build
plan is [.ai/PLAN.md](PLAN.md), live status in [.ai/STATUS.md](STATUS.md).

Derived from OGAP (`../Hushcrasher/`) but **deliberately simpler** — the north star is:
*"this engineer can build a production data platform for a startup"*, **not** *"the next dbt"*.

## General rules (project owner's standing directives)

1. **Be opinionated** — pick and defend one approach; don't present menus.
2. **Prefer simplicity over abstractions** — no new abstraction without two concrete call sites.
3. **Keep everything production-grade** — typed, tested, documented, observable.
4. **Explain every significant architectural change** (and ADR it).
5. **Preserve existing quality**; if something already satisfies the requirement, leave it.
6. **Do not introduce breaking complexity.**
7. **After significant work, summarize every architectural improvement.**

## The production path is lean and modern (keep it focused)

`Python → Prefect → Sources → [dlt direct | scrape→Postgres landing→dlt/ingestr] → Raw Parquet (PyArrow, FS/R2) → DuckDB → SQLMesh → analytics → FS → ML outputs.`
Ingestion default = **dlt** (`BaseSource` family); **ingestr** optional for CDC; scraped/parsed
data lands in the **Postgres `landing`** schema first. The **only** production transform engine
is **SQLMesh** (compiled from `spec/`, run on
DuckDB, sequenced by Prefect). Every other engine (plain-SQL runner, dbt, Bruin) and every
semantic/BI/feature-store *tool* (MetricFlow, Cube, Evidence, Feast, Airbyte) lives in
`experimental/` or `docs/comparisons/`, **consumes** `spec/`, and never sits on the default
`make`/pipeline path.

## Hard rules

1. **Layer naming is law** (ARCHITECTURE §): **raw (Layer 0)** `<system>__<table>` — 1:1 AS-IS,
   only optional `_ingested_at`/`etl_batch_id` added; `stg_*`; core entities/bridges (+ DV
   suffixes only for cross-source `game` identity); star `*_fact`/`*_dim`; **activity model**
   `am_<entity>_stream` (Activity Schema); marts with mandatory prefix `owt_*`/`agg_*`; feature
   store `fs_<entity>_<feature_group>`. **No medallion vocabulary.**
2. **`spec/` is the SSoT and engine-agnostic.** SQL is authored in **Bruin asset format**
   (SQL body + `@bruin` YAML: `depends`→lineage, `columns[].checks`→DQ, `owner`/`tags`→
   metadata); source contracts in **ODCS**. `spec/` must not require any engine binary to be
   read. The **spec compiler** renders spec → engine projects; the default runtime engine is
   **SQLMesh**. Engine specifics live only in the compiler and `spec/sql/_ext/<engine>/`.
3. **SSoT config**: every non-secret default is declared ONCE, in `config/config.yml`;
   `.env` is rendered by `config/.env-render.py`. Never duplicate a value another surface owns.
4. **Quality bar**: Ruff clean, Pyright **strict** 0 errors, pytest green (`make check` = CI).
   Typed Python, Pydantic v2 at boundaries, httpx + tenacity, loguru. **Logging: use the house
   alias `log`** — `from ogip.logger import log` and `log.info(...)` everywhere (never `logger.`);
   `logger` stays exported only for third-party compat.
5. **Secrets** (minimal & lightest): slot names declared once in `config/config.yml`; rendered
   `.env` always gitignored (templates carry blank slots only). Default = **gitignored `.env`**
   locally/VPS + **GitHub Actions secrets** in CI — no vault, no GPG. Bitwarden CLI & git-secret
   are opt-in (documented). Never commit plaintext secrets or bake keys into raw data.
6. **Contracts first**: dataset changes update the ODCS contract in `spec/contracts/<source>/`
   alongside the code.
7. **Portable SQL**: DuckDB/Postgres-first; engine-specific overrides isolated in
   `spec/sql/_ext/<engine>/`.
8. **Every new directory gets a `README.md`.** Architectural changes get an ADR.

## Run & orchestration profiles

Selected via `config/config.yml → run_profiles` + `just run-profile <name>`:
`prefect-sqlmesh` (default, production) · `prefect-sql` · `prefect-bruin` · `prefect-dbt` ·
`prefect-sqlmesh-over-dbt` · `prefect-dagster-dlt-dbt`. `prefect-bruin` and
`prefect-dagster-dlt-dbt` are **complete alternative setups**. Storage: `local` (default) ·
`r2` · `minio` · `s3`. Prefect runtime: `ephemeral` (default) · `server`. Secrets: gitignored
`.env` (default) + GitHub Actions secrets (CI); `bitwarden`/`git-secret` opt-in. dbt/SQLMesh/Bruin
projects are **generated from `spec/`** by the compiler, never hand-forked.

## Repo conventions

| Where | What |
|---|---|
| `.run/` | ALL runtime: venv (`UV_PROJECT_ENVIRONMENT=.run/venv`), caches, DuckDB warehouse, outputs (gitignored) |
| `.tmp/` | ALL temp/working scripts **and other temp files** (gitignored) + tracked `README.md` + `Justfile`; one-shots in `.tmp/.once/`; **graduate** durable ones → `integrations/`, skills, or `src/`/common |
| `../Hushcrasher.attic/` | External graveyard for removed legacy (never delete in place) |
| `Makefile` | **pipeline launcher**: one target per pipeline (`run-<engine>`, 1 op = 1 pipeline); a catch-all forwards any other `make <op>` → `just <op>` |
| `Justfile` | **every** developer/infra/spec op: gates (lint/typecheck/test/check/ci), up/down/obs/storage, run-profile, spec-compile, CI steps, generators |
| `.ai/` | agentic hub: AGENTS/CLAUDE/README/STATUS/PLAN + `tasks/`; root `AGENTS.md` is a symlink here |
| **Git LFS** | **large test datasets** (recorded fixtures, sampled dumps, parquet cases) are LFS pointers, never raw blobs — patterns in `.gitattributes` (format-scoped: binary formats on fixture paths; small JSON/text fixtures stay plain git so diffs read). One-time per clone: `make lfs-install`. Enforced un-skippably by `.ci/run.sh lfs-guard` (>512KB raw blob or LFS-attributed raw blob → CI red); local: `just lfs-guard` |

Workflow: **phased delivery with user approval gates** (plan in [PLAN.md](PLAN.md), near-term
actions in [TODO.md](TODO.md), status in [STATUS.md](STATUS.md), per-phase task files in
[tasks/](tasks/)). Tasks sync to **GitHub Issues/Projects** via `just tasks-sync` (single
tracker). Commits: Conventional Commits, split by category; no push without asking.
