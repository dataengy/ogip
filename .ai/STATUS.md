# OGIP — Status

_Last updated: 2026-07-17_

## Current phase

**M0 — walking skeleton: ✅ SHIPPED.** RAWG → raw Parquet (**dlt**) → **SQLMesh** (raw→stg→core→fs,
compiled from Bruin spec) → ML-ready `games.parquet` + `market_features.parquet` → demo notebook,
all driven by a **Prefect** flow (ephemeral, no Docker). `make check` green; **e2e test runs the
Prefect job in CI**; CI green (7/7). Repo: [github.com/dataengy/ogip](https://github.com/dataengy/ogip).
Detail: [tasks/m0-walking-skeleton.md](tasks/m0-walking-skeleton.md).

Phase 0 (scaffold) also ✅ shipped — [tasks/phase-0-scaffold.md](tasks/phase-0-scaffold.md).
Next: **M1–M4** — replicate the slice across toolsets (prefect-bruin, prefect-dbt,
prefect-sqlmesh-over-dbt, prefect-dagster-dlt-dbt); Evidence visualizer over the outputs; broaden.

## Done

- Project path created: `~/gi/@dataengy/OGIP`.
- Master creation plan written: [PLAN.md](PLAN.md) (target design + 11 phases + port map).
- `.ai/` hub scaffolded: AGENTS · CLAUDE · README · STATUS · PLAN · **TODO** · `tasks/`.
- `docs/` scaffolded: README · CHANGELOG · ROADMAP; **adr/** (index + template + 13 ADRs) ·
  **architecture/** (README + overview) · **runbooks/** (README + template + 4 runbooks).
- `.tmp/` (README + Justfile) for temp scripts/files.

## Decisions locked

| # | Decision |
|---|---|
| D0 | `spec/sql` in **Bruin asset format**; other spec entities in Bruin where possible; contracts in **ODCS**. Open authoring serialization, not a prod dependency. |
| D1 | dbt/SQLMesh/Bruin + orchestration profiles are **runnable** demos (in `experimental/`). |
| D2 | Storage: **local FS default** + **Cloudflare R2** (cloud of record) + **MinIO** + **S3** profiles. |
| D3 | Prefect **both** ephemeral (default) + server-in-compose profile. |
| D4 | Fast slice: Phases 0–6 on **Steam + RAWG** → end-to-end demo. |
| D5 | **Default transform engine = SQLMesh** (from spec, on DuckDB, orchestrated by Prefect); plain-SQL/dbt/Bruin = comparisons; needs the spec compiler. |
| D6 | Add **FS (Feature Store) layer** `fs_*` (SQL-as-FS → parquet) + adoption analysis of a dedicated FS tool. |
| D7 | **JupyterLab** + `notebooks/` demo notebooks (primary DS interface). |
| D8 | **Evidence** optional visualizer research for DA/DS/MLE. |
| D9 | Full stack wired: typed Python · uv · Prefect 3 · **PostgreSQL** (landing + platform_meta + Prefect) · **Cloudflare R2** · **Parquet/PyArrow** · DuckDB · **manual VPS deploy** (DevOps separate) · GitHub Actions (typecheck + tests). |
| D10 | **Secrets = minimal & lightest**: gitignored **`.env`** (slots from SSoT) locally+VPS + **GitHub Actions secrets** in CI. No vault/GPG by default; Bitwarden CLI & git-secret opt-in (documented). |
| D11 | **Ingestion: dlt default** (via `BaseSource`); **ingestr optional (CDC)**; scraped/parsed data lands in **PostgreSQL `landing`**, then dlt/ingestr load it to raw Parquet. |
| D12 | **Task tracking = GitHub Issues/Projects**: `.ai/tasks/` ↔ Issues/board via `just tasks-sync`; `.ai/TODO.md` = short ordered checklist referencing tasks. |
| D13 | **Add AM (Activity Model) layer** — Activity Schema `am_<entity>_stream`; complements Kimball STAR over CORE (4 modeling techniques showcased). |
| D14 | **Delivery = walking skeleton first** — smallest full slice (1 source→raw→spec→SQLMesh→ML parquet→notebook+Evidence, Prefect+dlt), then replicate across toolsets; **run in Docker + Prefect after each** (`integrations/prefect/`). |
| D15 | **Commit + push after every successful run** (green gate / green pipeline). |
| D16 | **Pre-commit via prek** (fast) — lint ALL (Python·SQL·Bash·YAML) + smoke tests on commit, data tests on pre-push, gitleaks. |
| D17 | **Test tiers** smoke / unit / integration / **e2e = run Prefect job + assert results**. |
| D18 | **Root-lean**: configs→`config/`, tests→`src/tests/`, scripts→`src/scripts/`, CI→`.ci/`; `structure-validate` guard. |
| D19 | **`.ai/` symlinks** for plans/memory/skills (memory·skills gitignored; specs·scripts tracked). |
| D20 | _(deferred)_ upsert code + scaffold **standards into `~/.ai/skills/.settings/code_specs/`** later. |
| + | Complete alt setups **Prefect+Bruin** & **Prefect+Dagster-over-dlt/dbt**; **CDC via ingestr** from the Postgres landing (optional). |

Assumptions: fresh `git init` · OGAP kept as sibling · GitHub Actions primary CI · package `ogip`.

Open design note: D0 (author in Bruin) + D5 (run on SQLMesh) implies a spec-compiler step —
flagged for the user; alternative is authoring natively in SQLMesh.

## Next steps

Plan finalized (D0–D14) incl. the walking-skeleton delivery strategy. Awaiting **go** to start building.

1. **Phase 0 — Scaffold & identity**: git init, pyproject/uv, tooling, config SSoT, secrets,
   CI, task-sync, `.run/`/`.tmp/`.
2. **M0 — walking skeleton**: RAWG → raw Parquet → 1st ODCS contract + Bruin SQL → SQLMesh
   (stg→core→mart/fs) → 1 ML `*.parquet` → 1 notebook + 1 Evidence page, on a Prefect flow (dlt).
   Then `make up` (Docker) + run the Prefect job green.
3. **M1–M4** — replicate the slice across the alt toolsets; broaden per Phases 4–10.

Open call: spec compiler kept (thin shim in M0, grown later) unless you say author-native-SQLMesh.
