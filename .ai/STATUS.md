# OGIP — Status

_Last updated: 2026-07-17_

## Current phase

**M0 — walking skeleton: ✅ SHIPPED.** RAWG → raw Parquet (**dlt**) → **SQLMesh** (raw→stg→core→fs,
compiled from Bruin spec) → ML-ready `games.parquet` + `market_features.parquet` → demo notebook,
all driven by a **Prefect** flow (ephemeral, no Docker). `make check` green; **e2e test runs the
Prefect job in CI**; CI green (7/7). Repo: [github.com/dataengy/ogip](https://github.com/dataengy/ogip).
Detail: [tasks/m0-walking-skeleton.md](tasks/m0-walking-skeleton.md).

Phase 0 (scaffold) also ✅ shipped — [tasks/phase-0-scaffold.md](tasks/phase-0-scaffold.md).

## Parallel-session lanes (claim a lock before writing!)

Work is split across concurrent agent sessions. **Claim your lane** with an object lock before
writing, and settle-check first (`git fetch` + `agent-lock check`):

```bash
bash ~/.ai/skills/_scripts/session/agent-session-lock.sh acquire --repo . --object <lane> --reason "..."
```

| Lane (lock object) | Scope | Owner |
|---|---|---|
| `core-pipeline` | `spec/` `src/ogip/` `ingestion/` `transform/` `pipelines/` `config/` `.ci/` | **this session** — M1 `prefect-bruin` · `prefect-dbt` · `prefect-sqlmesh-over-dbt` |
| `obs` | `deploy/obs/`, `src/scripts/obs-*.sh`, `docs/architecture/observability.md` | **parallel session** — Phase 7 stack shipped; 2 handoffs below |
| `evidence` | `experimental/bi/evidence/` | parallel session |
| `dagster` | `experimental/orchestration/dagster*`, `prefect-dagster-dlt-dbt` profile | parallel session |
| `vps` | `deploy/vps/`, `vps-*` recipes, `config/config.yml → deploy.vps.*` | **parallel session** — tooling shipped; 1 handoff below |
| `s3` | MinIO in `deploy/`, `storage` config, dlt/duckdb S3 destination | parallel session |

Use the **direct script**, not `just -f … agent-lock` — its recipe re-parses `--reason` through
`bash -c`, so parentheses break it.

### Handoffs: lane `obs` → lane `core-pipeline`

The Phase 7 stack is live (`make obs-up`), but its pipeline-facing half sits in **your** lane —
`config/` and `pipelines/` are locked to you, so the obs session did not touch them:

1. **The flow writes no log file** → Alloy tails an empty dir, log panels stay blank.
   `pipelines/flows/main.py:78` calls a bare `setup_logging()`; `src/ogip/config.py` already
   exposes both knobs it needs —
   `setup_logging(json_logs=settings.log_json, log_file=settings.log_file)`.
   Parsed Loki labels additionally need `platform.log_json: true` in `config/config.yml`.
2. **Obs ports never reach `.env`** → `config/config.yml` declares `victoriametrics_port`,
   `loki_port`, `grafana_port`, but `config/.env-render.py` → `_derived()` does not map them, so
   compose falls back to literals that duplicate the SSoT. Three lines close it.

Optional later: export OTLP metrics to `localhost:4318` (prefix `ogip_`) — Alloy already
receives them and the dashboard panel is waiting. Detail:
[docs/architecture/observability.md](../docs/architecture/observability.md) → "Not wired yet".

### Handoff: lane `vps` → lane `core-pipeline`

`deploy/vps/` is complete and verified ([tasks/vps-deploy-tooling.md](tasks/vps-deploy-tooling.md)),
but a real deploy still stops at preflight on one missing artifact in **your** lane:

- **`integrations/prefect/deploy.py` does not exist** → `just prefect-deploy` and `deploy.sh`
  step 5 have nothing to call. (`deploy/docker-compose.yml`, the other prerequisite, landed
  with the obs/compose lane on 2026-07-17.)

`deploy.sh` preflights and refuses to start rather than half-deploying, so this is a clean
block, not a landmine. Nothing else in `deploy/vps/` needs you: settings are read straight from
`config/config.yml → deploy.vps.*` via `yq`, so `config/.env-render.py` needed **no** change.

### Handoff: lane `s3` → lane `core-pipeline`

Object storage is shipped and verified ([tasks/s3-object-storage.md](tasks/s3-object-storage.md)):
`src/ogip/storage.py` resolves backend → bucket URL + credentials, `make storage-up` runs MinIO,
and a round-trip test proves dlt → `s3://` → DuckDB-over-`httpfs` for real. But **every call site
is in your lane**, so `local` is still the only backend the pipeline actually runs on. Nothing
below changes current behaviour — `local` stays the default until you land it.

1. **`ingestion/base/base_source.py:48`** hardcodes the local FS →
   `destination=dlt_filesystem_destination(data_dir)` (from `ogip.storage`). `run()` then returns
   the dataset **URL** (`str`, not `Path`); its only caller (`pipelines/flows/main.py:41`) already
   does `str(out)`, so the flow and its asset key are unaffected.
2. **`spec/sql/raw/*.sql` + the spec compiler** — ⚠️ **the real blocker.** Layer-0 hardcodes
   `read_parquet('.run/data/raw/rawg__games/*.parquet')`, so SQLMesh keeps reading the local FS
   no matter what dlt writes to `s3://`. The lake root must be **injected by the compiler**
   (D0/D5) rather than being a literal; `ogip.storage.raw_bucket_url()` returns exactly the
   prefix it needs.
3. **`transform/sqlmesh/config.yaml`** — config, not code: SQLMesh's `DuckDBConnectionConfig`
   supports both `extensions: [httpfs]` and `secrets:`, interpolated from the `OGIP_S3_*` slots.
   SQLMesh opens its own connection, so our `configure_duckdb_s3()` cannot reach it.
4. **`config/.env-render.py`** — add `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` plus matching
   `OGIP_S3_*` dev defaults to `DEMO_DEFAULTS` (the existing `OGIP_PG_PASSWORD` pattern), so
   `make storage-up` + `backend: minio` works from a bare checkout without hand-filling slots.

`src/ogip/warehouse.py` needs **nothing**: `export_table` reads the built warehouse, never `s3://`.

## Known-broken references

- `just prefect-deploy` / `prefect-run` → `integrations/prefect/{deploy,trigger}.py` — **missing**
  (core-pipeline lane; `integrations/` does not exist yet). `deploy/vps/smoke.sh` calls `trigger.py`.
- ~~`just tasks-sync` → `integrations/github/tasks_sync.py`~~ — **fixed** 2026-07-17: rewritten as
  `src/scripts/tasks_sync.py` (pyright-covered, unlike `integrations/`). Tracker is live:
  [issues #1–#3](https://github.com/dataengy/ogip/issues).

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
