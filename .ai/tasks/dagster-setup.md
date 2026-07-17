# Task — Dagster setup (dg CLI + Components, dev + prod)

**Status:** 🟡 in progress — dbt + dlt components run green; dev/prod configs in; ingestr CDC pending.

Alternative complete setup for the `prefect-dagster-dlt-dbt` profile (A12) — **off the
production path** (ADR-0007). Lives in `experimental/orchestration/dagster_ogip/` as a
self-contained uv project so Dagster's deps never touch the production env.

## Facts established (verified, not assumed)

- **There is no "Dagster 4"** — latest on PyPI is **1.13.14**; `dagster-dbt`/`dagster-dlt`/
  `dagster-postgres` are 0.29.14, `dagster-dg-cli` 1.13.14. The modern approach is the
  **`dg` CLI + Components**, which is what we use.
- Scaffolded with the real CLI: `uvx -U create-dagster project`, then
  `dg scaffold defs dagster_dbt.DbtProjectComponent dbt_ingest` and
  `dg scaffold defs dagster_dlt.DltLoadCollectionComponent dlt_ingest`.

## Delivered

- **spec → dbt compiler** (`src/ogip/spec_compile/to_dbt.py`) — `DbtProjectComponent` needs a
  real dbt project, but `spec/` stays SSoT (ADR-0005), so we generate one: Bruin
  schema-qualified deps → `{{ ref() }}`, Bruin `tags:` → dbt config tags (this is what makes
  `select: 'tag:daily'` work), Bruin column `checks` → dbt tests in `schema.yml`.
  Runtime paths are absolutized — dbt executes from the dbt project dir, so spec's
  repo-relative `.run/…` would otherwise silently resolve to nothing.
- **dbt component** — `defs/dbt_ingest/defs.yaml`: `project: "{{ project_root }}/dbt"`,
  `select: "tag:daily"`. The dbt manifest becomes Dagster assets.
- **Native dlt component** — `defs/dlt_ingest/{defs.yaml,loads.py}`: RAWG → raw Parquet, same
  Layer-0 contract as the Prefect lane, so dbt's `raw.rawg__games` reads identical data.
- **dev** (`deploy/dev/dagster.yaml`) — SQLite in `DAGSTER_HOME`, `DefaultRunCoordinator`, no infra.
- **prod** (`deploy/prod/dagster.yaml`) — Postgres storage via **env-refs only** (ADR-0011),
  `QueuedRunCoordinator`, retention. Reuses the platform Postgres (ADR-0008) on its own DB.

## Verified

- `dg check defs` → "All component YAML validated successfully. All definitions loaded successfully."
- `dg launch --assets '*'` → **RUN_SUCCESS**; `dbt build --select tag:daily`; PASS=12 ERROR=0
  (3 tables + 1 view + **8 data tests generated from Bruin checks**).
- **Asset selection prunes the graph**: `dg launch --assets 'key:"game"+'` → Dagster compiled it
  to `dbt build --select ogip.fs.market_features ogip.core.game` — PASS=7, not 12.
- Asset graph spans both integrations: `raw/rawg__games` (dlt, group `ingestion`) → `stg_games`
  → `game` → `market_features` (dbt).

## ingestr CDC (done)

One pipeline uses **CDC**, deliberately (D11): the Postgres `landing` zone (where scrapers write
continuously) is captured via **ingestr** logical replication, while batch API sources stay on dlt.

- `cdc/ingestr_cdc.sh` — `ingestr ingest` with a replication-slot/publication source URI,
  `--incremental-strategy merge`, `--stream` for continuous mode. Config from `OGIP_*` env only
  (ADR-0011); the printed command **redacts the password**. Verified via `--dry-run` (no live PG).
- `defs/cdc_ingest/definitions.py` — wraps it as the `cdc_landing` asset (kinds `ingestr`/
  `postgres`, group `ingestion`), so CDC sits in the same graph as the dlt load + dbt models.
- `dg check defs` green with all four pieces; `dg list defs` shows `cdc_landing`.

## Combo e2e (done)

`e2e/run_combo.sh` drives the **whole pipeline through Dagster** — SOURCE → FINAL LAYER on the
`dagster-dlt-dbt` combo (orchestrator Dagster · ingestion dlt · transform dbt · dq dbt tests):
compile `spec/`→dbt → `dg launch` dlt ingest → `dg launch` dbt build (models **+** tests) →
assert `fs.market_features` (rows>0, no null features). Green: `PASS=12`, `rows=5, nulls=0`.
A separate **`dagster-e2e`** GitHub workflow runs it (nested uv project; not part of core `ci.yml`).
`tests/test_e2e_combo.py` is a `pytest -m e2e` wrapper. Docs: [ADR-0015](../../docs/adr/ADR-0015-dagster-alt-orchestration-dg-components.md),
[runbook](../../docs/runbooks/run-dagster.md).

Fixes found while making it green: dagster-dlt defaulted to JSONL (pinned `file_format="parquet"`
on the resource + added pyarrow); DuckDB won't create its parent dir (`mkdir -p`); dbt flattened
layers into `main` (added `schema=<layer>` + a `generate_schema_name` macro), and the `raw` dbt
model's key collided with the dlt asset (left `raw` schema-unqualified — it is only a registration view).

## Next

- Verify **prod** + a live CDC run for real: needs Docker/Postgres with `wal_level=logical` +
  `CREATE PUBLICATION ogip_landing_pub FOR TABLES IN SCHEMA landing` (unavailable in this env).
- Wire `just run-profile prefect-dagster-dlt-dbt` to this project.
- Generated `dbt/` is a build artifact (gitignored) — regenerate via the compiler.
