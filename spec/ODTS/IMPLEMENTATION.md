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

### DQ projection: `checks:` → SQLMesh audits

`to_sqlmesh.py` (`_audits` / `_audit_for`) projects every `columns[].checks` entry — plus the
composite top-level `checks: [{name: unique, columns: [...]}]` form — into the `MODEL(...)`
block's `audits (...)` clause. This used to be a silent drop (`_model_text` emitted
`MODEL(name, kind)` and discarded `columns.checks` entirely); the compiler now renders every
check, and an unrecognized check name is a compile-time `SqlSpecError` — SPEC.md §5's
"attributes outside the check vocabulary MUST fail compilation" — never a silent skip.

| ODTS check | SQLMesh audit |
|---|---|
| `not_null` | `not_null(columns := (col))` |
| `unique` (column-level) | `unique_values(columns := (col))` |
| `non_negative` | `accepted_range(column := col, min_v := 0)` |
| `between(a, b)` | `accepted_range(column := col, min_v := a, max_v := b)` |
| `accepted_values(v1, ...)` | `accepted_values(column := col, is_in := (v1, ...))` |
| top-level `unique(columns: [...])` | `unique_combination_of_columns(columns := (...))` |
| anything else | compile-time `SqlSpecError` — never silently dropped |

70 audits render this way across raw/staging/core/fs today (the comprehensive-DQ pass of the
[transform-expansion plan](../../docs/superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md)).

**ODTS §6 boundary — checks ≠ monitors.** Only correctness constraints (the table above) belong
in `columns[].checks:`. Freshness and row-count **monitors** are a separate concern, declared in
[`spec/dq/policy.yml`](../dq/policy.yml) — never in `spec/sql` `checks:` — and are loaded +
reported (not yet executed) by [`dq/run.py`](../../dq/run.py); the executor (query the
warehouse, evaluate thresholds, record to `platform_meta.dq_results`) is Phase 4. A `checks:`
entry shaped like a monitor (`freshness`, `row_count`) is a spec defect, not an alternate
authoring style.

**Known gap — audits are compiled but not executed by the default gate.** `make check` runs
`pytest -m "not integration and not e2e"`; the generated `audits (...)` clauses are only
evaluated when SQLMesh actually plans/applies against a warehouse (`sqlmesh plan --auto-apply`),
which happens in `src/tests/e2e/test_all_setups.py::test_base_setup_builds_and_produces_ml -k
sqlmesh` (marked `e2e`, excluded from `make check`) or a live `prefect-sqlmesh` run. A regression
in a rendered `not_null`/`accepted_range` audit can compile clean and pass `make check` while
still being broken at run time — only the e2e test (or a manual `sqlmesh audit` run) catches it.
See [ADR-0019](../../docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md).

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
