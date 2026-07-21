# ODTS 0.1 — the OGIP implementation, described

This document describes OGIP's transformation stack in the standard's terms:
[`spec/sql/`](../sql/AGENTS.md) is the authoring layer,
[`src/ogip/spec_compile/`](../../src/ogip/spec_compile/) is the compiler, and
[`transform/`](../../transform/README.md) holds the six compiled projections. The sibling
document for orchestration is [ODOS IMPLEMENTATION](../ODOS/IMPLEMENTATION.md).

## Status at a glance

| ODTS layer | State |
|---|---|
| Authoring documents | six models in `spec/sql/`, currently on the legacy `@bruin` header; `@odts` migration is [#35](https://github.com/dataengy/ogip/issues/35) |
| Frontend (`@odts` → legacy YAML) | planned — [#35](https://github.com/dataengy/ogip/issues/35) |
| Macro registry (`@keys.hash`, `@dates.year`) | planned — [#36](https://github.com/dataengy/ogip/issues/36); surrogate keys are hand-written `md5(...)` today |
| IR + adapters (six targets) | **live** — `parse_asset()` → `Asset` → `to_sqlmesh` · `to_dbt` · `to_bruin` · `to_sqlmesh_dbt`; plain SQL consumes `spec/sql` directly |
| Lineage, ref-rewriting, retargeting | **live** — `spec_compile/dialect.py` (sqlglot), AST-scoped |
| Formatter | **live** — sqlfluff, sole formatter (`just sql-lint`) |

## 1. The authoring layer — `spec/sql`

Six documents, one per model, path = `<layer>/<name>.sql`, building
`raw → staging → core → fs` (layer naming is project law — no medallion vocabulary):

| Model | Kind | Semantic class (tags) | Declared constraints |
|---|---|---|---|
| `raw.rawg__games` | view | `raw, rawg, daily` | none — 1:1 registration of the immutable raw Parquet |
| `raw.metacritic__game` | view | `raw, metacritic, daily` | none — 1:1 registration of the immutable raw Parquet |
| `staging.stg_games` | table | `staging, rawg, daily` | `game_id` !null unique · `name` !null |
| `staging.stg_metacritic_games` | table | `staging, metacritic, daily` | `slug` !null unique · `name` !null · `metascore` non_negative |
| `core.game` | table | `core, entity, daily` | `game_sk` pk !null unique · `title` !null |
| `fs.market_features` | table | `fs, feature-store, daily` | `game_sk` !null unique · `popularity_score` non_negative |

The dependency chain is exactly what §4 of the [profile](SPEC.md) says it should be: derivable
from the SQL AST, so the `@odts` form of these documents authors no `depends` at all — see
[`examples/`](examples/README.md), which re-headers precisely these four models.

## 2. The compiler — `src/ogip/spec_compile`

The IR pipeline of SPEC.md §9 as it exists today:

- `parse_asset()` reads the header into the typed `Asset` — the canonical model; the header
  text never is.
- `dialect.py` (sqlglot) owns everything that must understand the SQL: `table_refs()`
  (lineage — the graph ODOS `select:` expansion consumes), `rewrite_refs()` (AST-scoped
  `staging.stg_games` → `{{ ref('stg_games') }}`), `transpile()` (DuckDB → Postgres /
  ClickHouse / BigQuery, exercised by tests on every run).
- The `@odts` frontend ([#35](https://github.com/dataengy/ogip/issues/35)) extends this at the
  front — rendering the compact header to the legacy `@bruin` YAML text that `parse_asset()`
  and one verbatim-copying target already require — and rewrites nothing behind it.

## 3. The six projections — `transform/`

Every directory is **generated from `spec/`**; none is hand-authored.
[`transform/engines.py`](../../transform/engines.py) regenerates an engine's project from the
spec immediately before running it, so a stale checkout cannot drift from the SSoT.

| Target | Adapter | Lives in | Run profile | Role |
|---|---|---|---|---|
| SQLMesh | `to_sqlmesh.py` | `transform/sqlmesh/` | `prefect-sqlmesh` | **production default** |
| dbt | `to_dbt.py` | `transform/dbt/` | `prefect-dbt`, `prefect-dagster-dlt-dbt` | comparison; also the project Dagster's `DbtProjectComponent` loads |
| OpenDBT | `to_dbt.py` | `transform/opendbt/` | `prefect-opendbt` | comparison (dbt-core extended) |
| SQLMesh-over-dbt | `to_sqlmesh_dbt.py` | `transform/sqlmesh_dbt/` | `prefect-sqlmesh-over-dbt` | comparison |
| Bruin | `to_bruin.py` | `transform/bruin/` | `prefect-bruin` | comparison — assets copied verbatim (the legacy header *is* Bruin's format) |
| plain SQL | none — consumes `spec/sql` directly | `transform/runner.py` | `prefect-sql` | comparison — topo-sorts `depends`, `create or replace` on DuckDB |

Generated projects are committed (reviewable diffs when the spec changes) and carry
repo-relative paths. Column `checks` become dbt `schema.yml` tests, Bruin checks, SQLMesh
audits — one declaration, per-target rendering, as SPEC.md §6 requires.

The boundary the standards family draws is visible in this table's consumers: Prefect and
Dagster appear nowhere in it. Orchestrators consume these compiled projects through the ODOS
task registry (`dbt.build` regenerates-then-builds; `build_warehouse("sqlmesh")` compiles then
plans) — they are ODOS's axis, never ODTS targets.

## 4. Conformance status against SPEC.md §9

| Requirement | Status |
|---|---|
| Target regeneration + committed-output identity | **green** — `just spec-compile all` · `just spec-verify` |
| Dialect retargeting stays parseable | **green** — retarget tests run per-model on every `make check` |
| Fixture/spec identity for the standard package | **green** — `just standards-validate` |
| `@odts` round-trip (rendered legacy header ≡ hand-written) | pending [#35](https://github.com/dataengy/ogip/issues/35) |
| `depends` assertion fails on AST disagreement | pending [#35](https://github.com/dataengy/ogip/issues/35) |
| LValue `:=` desugar / `=` rejection | pending [#35](https://github.com/dataengy/ogip/issues/35) |
| Macro conformance (byte-identical per adapter) | pending [#36](https://github.com/dataengy/ogip/issues/36) |
